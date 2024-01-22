# Scheduler Architecture

## Purpose

The _scheduler_ is tasked with populating and maintaining a priority queue of
items that are ranked, and can be popped off through HTTP API calls.
The scheduler is designed to be extensible, such that you're able to create
your own rules for the population, and prioritization of tasks.

The _scheduler_ implements a priority queue for prioritization of tasks to be
performed by the worker(s). In the implementation of the scheduler within KAT
the scheduler is tasked with populating the priority queue with 'boefje' and
'normalizer' tasks. Additionally the scheduler is responsible for maintaining
and updating its internal priority queue.

A priority queue is used, in as such, that it allows us to determine what tasks
should be picked up first, or more regularly. Because of the use of a priority
queue we can differentiate between tasks that are to be executed first, e.g.
tasks created by the user get precedence over tasks that are created by the
internal rescheduling processes within the scheduler.

Calculations in order to determine the priority of a task is performed by the
`ranker` that leverages information from multiple (external) sources,
called `connectors`.

In this document we will outline how the scheduler operates within KAT, how
iternal systems function and how external services use it.

## Architecture / Design

In order to get a better overview of how the scheduler is implemented we will
be using the [C4 model](https://c4model.com/) to give an overview of the
scheduler system with their respective level of abstraction.

### C2 Container level:

First we'll review how the `Scheduler` system interacts and sits in between its
external services. In this overview arrows from external services indicate how
and why those services communicate with the scheduler. The `Scheduler` system
combines data from the `Octopoes`, `Katalogus`, `Bytes` and `RabbitMQ` systems.

```mermaid
graph TB

    Rocky["Rocky<br/>[webapp]"]
    Octopoes["Octopoes<br/>[graph database]"]
    Katalogus["Katalogus<br/>[software system]"]
    Bytes["Bytes<br/>[software system]"]
    RabbitMQ["RabbitMQ<br/>[message broker]"]
    Scheduler["Scheduler<br/>[system]"]
    TaskRunner["Task Runner<br/>[software system]"]

    Rocky--"Create object"-->Octopoes
    Rocky--"Create scan job<br/>HTTP POST"--->Scheduler

    Octopoes--"Get random oois<br/>HTTP GET"-->Scheduler

    RabbitMQ--"Get latest created oois<br/>Get latest raw files<br/>AMQP"-->Scheduler

    Katalogus--"Get available plugins<br/>HTTP GET"-->Scheduler
    Bytes--"Get last run boefje<br/>HTTP GET"-->Scheduler

    Scheduler--"Pop task of queue"-->TaskRunner
```

### C3 Component level:

When we take a closer look at the `scheduler` system itself we can identify
several components. The 'Scheduler App' directs the creation and maintenance
of a multitude of schedulers. Typically in a KAT installation, 2 schedulers
will be created per organisation: a boefje scheduler and a normalizer scheduler.

Each scheduler can implement it's own way of populating, and prioritization of
its queue. The associated queues of an individual scheduler is persisted in
a SQL database table.

```mermaid
C4Component
    title Component diagram for Scheduler

    Container_Boundary(database, "PostgreSQL Database") {
        ContainerDb(tbl_jobs, "jobs", "table", "Definition of recurring tasks")
        ContainerDb(tbl_items, "items", "table", "Priority Queue `p_item`")
        ContainerDb(tbl_tasks, "tasks", "table", "History of current and previous tasks`")
        ContainerDb(tbl_events, "events", "table", "Change events relating to tasks")
    }

    Container_Boundary(scheduler_app, "Scheduler App") {
        Container_Boundary(schedulers, "Schedulers") {
            Component(boefje_scheduler_a, "Boefje Scheduler Org A", "Scheduler", "")
            Component(normalizer_scheduler_a, "Normalizer Scheduler Org A", "Scheduler", "")
            Component(boefje_scheduler_b, "Boefje Scheduler Org B", "Scheduler", "")
            Component(normalizer_scheduler_b, "Normalizer Scheduler Org B", "Scheduler", "")
        }

    Container_Boundary(server, "Server") {
        Component(server, "Server", "REST API")
    }
}
```

**Boefje Scheduler**

```mermaid
C4Component
    Container_Boundary(boefje_scheduler, "Boefje Scheduler", "Scheduler") {
        Component("mutations", "Scan Profile Mutations", "Method running in Thread", "...")
        Component("new_boefjes", "New Boefjes", "Method running in Thread", "...")
        Component("reschedule", "Rescheduling", "Method running in Thread", "...")

        UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")

        Component("push_task_boefje", "Push Task", "Method")

        SystemQueue(pq_boefje, "PriorityQueue", "Persisted in a postgresql database table")
    }

    Rel(mutations, push_task_boefje, "", "")
    Rel(new_boefjes, push_task_boefje, "", "")
    Rel(reschedule, push_task_boefje, "", "")
    Rel(push_task_boefje, pq_boefje, "", "")
```

**Normalizer Scheduler**

```mermaid
C4Component
    Container_Boundary(boefje_scheduler, "Boefje Scheduler", "Scheduler") {
        Component("raw_file_received", "Raw File Received", "Thread", "...")

        UpdateLayoutConfig($c4ShapeInRow="1", $c4BoundaryInRow="1")

        Component("push_task_normalizer", "Push Task", "Method")

        SystemQueue(pq_normalizer, "PriorityQueue", "Persisted in a postgresql database table")
    }

    Rel(raw_file_received, push_task_normalizer, "", "")
    Rel(push_task_normalizer, pq_normalizer, "", "")
```

A more complete overview of the different components within the scheduler app:

```mermaid
C4Component
    title Component diagram for Scheduler

    SystemQueue_Ext(rabbitmq_scan_profile_mutations, "RabbitMQ", "scan_profile_mutations")
    SystemQueue_Ext(rabbitmq_raw_file_received, "RabbitMQ", "raw_file_received")

    System_Ext("katalogus", "Katalogus", "...")
    System_Ext("rocky", "Rocky", "...")
    System_Ext("bytes", "Bytes", "...")
    System_Ext("octopoes", "Octopoes", "...")

    Container_Boundary("scheduler_app", "Scheduler App") {

        %% ContainerDb(pq_store, "Priority Queue Store", "postgresql DatabaseTable", "...")

        Container_Boundary(boefje_scheduler, "Boefje Scheduler", "Scheduler") {
            Component("scan_profile_mutations", "Scan Profile Mutations", "Thread", "...")
            Component("new_boefjes", "New Boefjes", "Thread", "...")
            Component("random_objects", "Random Objects", "Thread", "...")

            Component("push_task_boefje", "Push Task", "Method")

            SystemQueue(priority_queue_boefje, "PriorityQueue", "Persisted in a postgresql database table")
        }

        Container_Boundary(normalizer_scheduler, "Normalizer Scheduler", "Scheduler") {
            Component("raw_file_received", "Raw File Received", "Thread", "...")

            Component("push_task_normalizer", "Push Task", "Method")

            SystemQueue(priority_queue_normalizer, "PriorityQueue", "Persisted in a postgresql database table")
        }

        Container_Boundary(server, "Server", "REST API") {
            Component("api_tasks", "/tasks", "...")
            Component("api_queues_push", "/queues/{id}/push", "...")
            Component("api_queues_pop", "/queues/{id}/pop", "...")
        }

        ContainerDb(task_store, "Task Store", "postgresql Database Table", "Persisted in a postgresql database table")
    }

    %% Boefje Scheduler
    Rel(scan_profile_mutations, rabbitmq_scan_profile_mutations, "AMQP", "...")
    Rel(scan_profile_mutations, push_task_boefje, "", "...")
    UpdateRelStyle(scan_profile_mutations, rabbitmq_scan_profile_mutations, $offsetX="-50")

    Rel(new_boefjes, katalogus, "HTTP", "...")
    Rel(new_boefjes, push_task_boefje, "", "...")
    UpdateRelStyle(new_boefjes, katalogus, $offsetX="10")

    Rel(random_objects, octopoes, "HTTP", "...")
    Rel(random_objects, push_task_boefje, "", "...")
    UpdateRelStyle(new_boefjes, katalogus, $offsetX="60")

    Rel(push_task_boefje, priority_queue_boefje, "push to queue", "...")
    Rel(push_task_boefje, task_store, "post push", "...")

    %% Normalizer Scheduler
    Rel(raw_file_received, rabbitmq_raw_file_received, "AMQP", "...")
    Rel(raw_file_received, push_task_normalizer, "", "...")

    Rel(push_task_normalizer, bytes, "", "")
    Rel(push_task_normalizer, priority_queue_normalizer, "push to queue", "...")
    Rel(push_task_normalizer, task_store, "post push", "...")

    %% Server
    Rel(priority_queue_boefje, api_queues_pop, "pop", "")
    Rel(api_queues_push, priority_queue_boefje, "push", "")
    Rel(priority_queue_normalizer, api_queues_pop, "pop", "")
    Rel(api_queues_push, priority_queue_normalizer, "push", "")
    Rel(task_store, api_tasks, "GET", "")

    %% Rocky
    Rel(rocky, api_queues_push, "POST", "")
    Rel(rocky, api_queues_pop, "GET", "")
    Rel(rocky, api_tasks, "GET", "")

    UpdateLayoutConfig($c4ShapeInRow="4", $c4BoundaryInRow="2")
```

## Dataflows

Following we review how different dataflows, from the `boefjes` and the
`normalizers` are implemented within the `Scheduler` system. The following
events within a KAT installation will trigger dataflows in the `Scheduler`.
With the current implementation of the scheduler we identify the creation of
two different type of tasks, `boefje` and `normalizer` tasks.

A graphical representation of task creation dataflows:

```mermaid
flowchart LR
  rmq_scan_profile([scan profile mutations])
  rmq_raw_file([raw file received])

  subgraph mula
    subgraph boefje scheduler organisation 1

      pq_boefjes(priority queue boefjes)

      subgraph threads_boefje["threads"]
        thread_scan_profile[[scan profile mutations]]
        thread_enabled_boefjes[[enabled boefjes]]
        thread_reschedule[[rescheduler]]
      end

      ranker_boefje{{ranker}}

    end

    thread_scan_profile-->ranker_boefje
    thread_enabled_boefjes-->ranker_boefje
    thread_reschedule-->ranker_boefje
    ranker_boefje-->pq_boefjes

    subgraph normalizer scheduler organisation 1

      pq_normalizer(priority queue normalizer)

      subgraph threads_normalizer["threads"]
        thread_raw_file_received[[raw file received]]
      end

      ranker_normalizer{{ranker}}
    end

    thread_raw_file_received-->ranker_normalizer
    ranker_normalizer-->pq_normalizer

    subgraph server
    end

    pq_boefjes<-->server
    pq_normalizer<-->server
  end

  rmq_scan_profile-->thread_scan_profile
  rmq_raw_file-->thread_raw_file_received

style thread_scan_profile stroke-dasharray: 5 5
style thread_enabled_boefjes stroke-dasharray: 5 5
style thread_reschedule stroke-dasharray: 5 5
style thread_raw_file_received stroke-dasharray: 5 5
```

### Boefje scheduler

For a `boefje` scheduler the following events will trigger a dataflow procedure
to be executed and subsequently the creation of a `boefje` task:

1. **scan profile mutation**: the scan profile level of an ooi increased
2. **enabled boefje**: a boefje has been enabled
3. **rescheduling**: a prior task has been rescheduled
4. **scan initiated**: from the webapp rocky a scan has been initiated

**1. Scan profile mutation**

```mermaid
                                                        flowchart LR
  rmq_scan_profile([scan profile mutations])

  subgraph mula
    subgraph boefje scheduler organisation 1

      pq_boefjes(priority queue boefjes)

      subgraph threads_boefje["threads"]
        thread_scan_profile[[scan profile mutations]]
      end

      ranker_boefje-->pq_boefjes
      ranker_boefje{{ranker}}

    end

    thread_scan_profile-->ranker_boefje

    subgraph server
    end

    pq_boefjes-->server

  end

  rmq_scan_profile-->thread_scan_profile

style thread_scan_profile stroke-dasharray: 5 5
```

When a scan level is increased on an OOI
(`schedulers.boefje.push_tasks_for_scan_profile_mutations`) the following will
happen:

- When scan level mutation occurs, the `Scheduler` system will get the
  scan profile mutation from the `RabbitMQ` system.

- For the associated OOI of this scan profile mutation, the `Scheduler`
  system will fetch the enabled boefjes for this OOI. (`tasks = ooi * boefjes`)

- For each enabled boefje, a `BoefjeTask` will be created and added to the
  `PriorityQueue` of the `BoefjeScheduler` as a 'PrioritizedItem`.
A `BoefjeTask` is an object with the correct specification for the task
  runner to execute a boefje.

- Each task will be checked if it is:

  - `is_allowed_to_run()`

  - `is_task_running()`

  - `has_grace_period_passed()`

  - `is_item_on_queue_by_hash()`

- The `BoefjeScheduler` will then create a `PrioritizedItem` and pushes it to
  the queue. The `PrioritizedItem` will contain the created `BoefjeTask` within
  a data field.

- The `BoefjeTask` will be added to the database (`post_push()`). And serves
  as a log of the current and prior tasks that have been queued/executed,
  and can be queried through the API.

```mermaid
sequenceDiagram
    participant Scheduler

    %% enable when github uses v10.3.0+ of mermaid
    %% create participant RabbitMQ
    %% scheduler->>rabbitmq: consume scan_profile_mutations
    %% destroy rabbitmq
    %% rabbitmq->>scheduler: consume scan_profile_mutations

    participant RabbitMQ
    participant Katalogus
    participant Bytes
    participant TaskStore
    participant PriorityQueueStore

    Scheduler->>RabbitMQ: consume scan_profile_mutations
    RabbitMQ->>Scheduler: consume scan_profile_mutations

    rect rgb(242, 242, 242)
    note right of Scheduler: get_boefjes_for_ooi()
        Scheduler->>Katalogus: get_boefjes_by_type_and_org()
    end

    Scheduler->>Scheduler: Create BoefjeTask objects
    Scheduler->>Scheduler: is_task_allowed_to_run()

    rect rgb(242, 242, 242)
    note right of Scheduler: is_task_running()
        Scheduler->>TaskStore: get_latest_task_by_hash()
        Scheduler->>Bytes: get_last_run_boefje()
    end

    rect rgb(242, 242, 242)
    note right of Scheduler: has_grace_period_passed()
        Scheduler->>TaskStore: get_latest_task_by_hash()
        Scheduler->>Bytes: get_last_run_boefje()
    end

    rect rgb(242, 242, 242)
    note right of Scheduler: is_item_on_queue_by_hash()
        Scheduler->>PriorityQueueStore: get_latest_task_by_hash()
    end

    Scheduler->>Scheduler: Create PrioritizedItem
    Scheduler->>PriorityQueueStore: push_item_to_queue_with_timeout()
```

**2. Enabled Boefjes**

When a plugin of type `boefje` is enabled or disabled in the Katalogus. The
scheduler will take notice of it by referencing its internal cache of all
the available plugins of an organisation. This will happen after:

- The cache of the organisation is flushed at a specified interval.

- Due to the flushing of the cache we get a new list of enabled boefjes for
  an organisation will be created.
  (`connectors.services.katalogus._flush_organisations_boefje_type_cache()`)

- New tasks will be created for enabled boefjes.

```mermaid
sequenceDiagram
    participant Scheduler

    participant Katalogus
    participant Octopoes
    participant Bytes
    participant TaskStore
    participant PriorityQueueStore

    Scheduler->>Katalogus: get_new_boefjes_by_org_id()

    loop for boefje in new_boefjes
        Scheduler->>Octopoes: get_objects_by_object_types()
    end

    rect rgb(191, 223, 255)
    note right of Scheduler: push_task()
        Scheduler->>Scheduler: Create BoefjeTask object
        Scheduler->>Scheduler: is_task_allowed_to_run()

        rect rgb(242, 242, 242)
        note right of Scheduler: is_task_running()
            Scheduler->>TaskStore: get_latest_task_by_hash()
            Scheduler->>Bytes: get_last_run_boefje()
        end

        rect rgb(242, 242, 242)
        note right of Scheduler: has_grace_period_passed()
            Scheduler->>TaskStore: get_latest_task_by_hash()
            Scheduler->>Bytes: get_last_run_boefje()
        end

        rect rgb(242, 242, 242)
        note right of Scheduler: is_item_on_queue_by_hash()
            Scheduler->>PriorityQueueStore: get_latest_task_by_hash()
        end

        Scheduler->>Scheduler: Create PrioritizedItem
        Scheduler->>PriorityQueueStore: push_item_to_queue_with_timeout()
    end
```

**3. Rescheduling**

For every `Task` that has been created within the scheduler a `Job` is created
for it. A `Job` contains the blueprint of an executed `Task` and is wrapped
within a `PrioritizedItem` so that it can be pushed onto the queue. A `Job` has
a 1:m relation to executed tasks.

These `Job` models allow us to keep track of tasks that need to be
rescheduled and executed at another time in the future. Either by calculation
(calculation of a new deadline), or by specification (adding a cron expression).

The scheduler continuously checks for jobs where their deadline has passed:

- Get all jobs for which the deadline has passed
- Evaluate job (are we able to run the job, for instance a boefje scheduler: is
  the ooi available, is boefje available, are scan levels correct)
- Calculate priority, and push to queue
- Calculate and set deadline (using information about the results of the task)
  for the job on signal job of finished

```mermaid
sequenceDiagram
    participant Scheduler

    participant JobStore
    participant TaskStore
    participant Katalogus
    participant Octopoes
    participant Bytes
    participant PriorityQueueStore

    Scheduler->>JobStore: jobs = get_jobs()  // Get all jobs where the deadline has passed

    loop for job in jobs
        Scheduler->>Katalogus: get_boefjes()
        Scheduler->>Scheduler: is boefje enabled?
        Scheduler->>Scheduler: ooi still existing?
        Scheduler->>Scheduler: boefje can still consume ooi?
        Scheduler->>Scheduler: boefje allowed to scan ooi??
    end

    rect rgb(191, 223, 255)
    note right of Scheduler: push_task()
        Scheduler->>Scheduler: Create BoefjeTask object
        Scheduler->>Scheduler: is_task_allowed_to_run()

        rect rgb(242, 242, 242)
        note right of Scheduler: is_task_running()
            Scheduler->>TaskStore: get_latest_task_by_hash()
            Scheduler->>Bytes: get_last_run_boefje()
        end

        rect rgb(242, 242, 242)
        note right of Scheduler: has_grace_period_passed()
            Scheduler->>TaskStore: get_latest_task_by_hash()
            Scheduler->>Bytes: get_last_run_boefje()
        end

        rect rgb(242, 242, 242)
        note right of Scheduler: is_item_on_queue_by_hash()
            Scheduler->>PriorityQueueStore: get_latest_task_by_hash()
        end

        Scheduler->>Scheduler: Create PrioritizedItem
        Scheduler->>PriorityQueueStore: push_item_to_queue_with_timeout()
    end

    rect rgb(191, 223, 255)
    note right of Scheduler: post_push()
        Scheduler->>TaskStore: get_task_by_id()
        alt task is None
            Scheduler->>TaskStore: create_task()
        else task is not None
            Scheduler->>TaskStore: update_task()
        end

        Scheduler->>JobStore: get_job_by_hash()
        alt job is None
            Scheduler->>JobStore: create_job()
        else job is not None
            Scheduler->>JobStore: update_job()
        end
    end
```

**4. Scan initiated**

Scan jobs created by the user in Rocky (`server.push_queue`), these tasks will
get the highest priority of 1. Note, that this will circumvent all the checks
that are present in

- Rocky will create a `BoefjeTask` that will be pushed directly to the
  specified queue.

```mermaid
sequenceDiagram
    participant Rocky
    participant Server
    participant Scheduler
    participant PriorityQueueStore

    Rocky->>Server: POST /queues/{queue_id}/push
    Server->>Scheduler: push_item_to_queue()
    Scheduler->>PriorityQueueStore: push()
```

### Normalizer Scheduler

For a `normalizer` task the following events will trigger a dataflow procedure

1. **raw file received**: bytes creates a signal on the message queue that
   it created a raw file.

\*_ 1. Raw file received_

When a raw file is created (`schedulers.normalizer.create_tasks_for_raw_data`)

- The `NormalizerScheduler` retrieves raw files that have been created in
  Bytes from a message queue.

- For every mime type of the raw file, the `NormalizerScheduler` will
  retrieve the enabled normalizers for this mime type.
  (`create_tasks_for_raw_data()`)

- For every enabled normalizer, a `NormalizerTask` will be created and added
  to the `PriorityQueue` of the `NormalizerScheduler`.

```mermaid
sequenceDiagram
    participant Scheduler

    %% enable when github uses v10.3.0+ of mermaid
    %% create participant RabbitMQ
    %% Scheduler->>RabbitMQ: consume raw_file_received
    %% destroy RabbitMQ
    %% RabbitMQ->>Scheduler: consume raw_file_received

    participant RabbitMQ
    participant Katalogus
    participant Bytes
    participant TaskStore
    participant PriorityQueueStore

    Scheduler->>RabbitMQ: consume raw_file_received
    RabbitMQ->>Scheduler: consume raw_file_received

    loop for mime_type in raw_file.mime_types
        Scheduler->>Katalogus: get_normalizers_for_mime_type()
    end

    rect rgb(191, 223, 255)
    note right of Scheduler: push_task()
        Scheduler->>Scheduler: Create NormalizerTask object
        Scheduler->>Scheduler: is_task_allowed_to_run()

        rect rgb(242, 242, 242)
        note right of Scheduler: is_task_running()
            Scheduler->>TaskStore: get_latest_task_by_hash()
            Scheduler->>Bytes: get_last_run_boefje()
        end

        rect rgb(242, 242, 242)
        note right of Scheduler: has_grace_period_passed()
            Scheduler->>TaskStore: get_latest_task_by_hash()
            Scheduler->>Bytes: get_last_run_boefje()
        end

        rect rgb(242, 242, 242)
        note right of Scheduler: is_item_on_queue_by_hash()
            Scheduler->>PriorityQueueStore: get_latest_task_by_hash()
        end

        Scheduler->>Scheduler: Create PrioritizedItem
        Scheduler->>PriorityQueueStore: push_item_to_queue_with_timeout()
    end


    Scheduler->>Scheduler: Create PrioritizedItem
    Scheduler->>PriorityQueueStore: push_item_to_queue_with_timeout()
```

The following describes the main components of the scheduler application:

- `App` - The main application class, which is responsible for starting the
  schedulers. It also contains the server, which is responsible for handling
  the rest api requests. The `App` implements multiple `Scheduler` instances.
  The `run()` method starts the schedulers, the listeners, the monitors, and
  the server in threads. The `run()` method is the main thread of the
  application.

- `Scheduler` - And implementation of a `Scheduler` class is responsible for
  populating the queue with tasks. Contains has a `PriorityQueue` and a
  `Ranker`. The `run()` method starts executes threads and listeners, which
  fill up the queue with tasks.

- `PriorityQueue` - The queue class, which is responsible for storing the
  tasks.

- `Ranker` - The ranker class, which is responsible for ranking the tasks,
  and can be called from the `Scheduler` class in order to rank the tasks.

- `Server` - The server class, which is responsible for handling the HTTP
  requests.
