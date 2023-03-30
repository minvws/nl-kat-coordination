# Design scheduler

## Purpose

The *scheduler* is tasked with populating and maintaining a priority queue of
items that are ranked, and can be popped off (through api calls).
The scheduler is designed to be extensible, such that you're able to create
your own rules for the population, and prioritization of tasks.

The *scheduler* implements a priority queue for prioritization of tasks to be
performed by the worker(s). In the implementation of the scheduler within KAT
the scheduler is tasked with populating the priority queue with 'boefje' and
'normalizer' jobs. The scheduler is responsible for maintaining and updating
its internal priority queue.

A priority queue is used, in as such, that it allows us to determine what jobs
should be checked first, or more regularly. Because of the use of a priority
queue we can differentiate between jobs that are to be executed first, e.g.
jobs created by the user get precedence over jobs that are created by the
internal rescheduling processes within the scheduler.

Calculations in order to determine the priority of a job is performed by logic
that can/will leverage information from multiple (external) sources, called
`connectors`.

In this document we will outline what the scheduler does in the setup within
KAT and how it is used.

### Architecture / Design

In order to get a better overview of how the scheduler is implemented we will
be using the [C4 model](https://c4model.com/) to give an overview of the
scheduler system with their respective level of abstraction.

#### C2 Container level:

First we'll review how the `Scheduler` system interacts and sits in between its
external services. In this overview arrows from external services indicate how
and why those services communicate with the scheduler.

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

* The `Scheduler` system combines data from the `Octopoes`, `Katalogus`,
`Bytes` and `RabbitMQ` systems.

```mermaid
flowchart TB
    subgraph Scheduler["SchedulerApp [system]"]
        subgraph OrganizationA["Organization A"]
            subgraph BoefjeSchedulerA["BoefjeScheduler [class]"]
                BoefjePriorityQueueA(["PriorityQueue"])
            end

            subgraph NormalizerSchedulerA["NormalizerScheduler [class]"]
                NormalizerPriorityQueueA(["PriorityQueue"])
            end
        end

        subgraph OrganizationB["Organization B"]
            subgraph BoefjeSchedulerB["BoefjeScheduler [class]"]
                BoefjePriorityQueueB(["PriorityQueue"])
            end

            subgraph NormalizerSchedulerB["NormalizerScheduler [class]"]
                NormalizerPriorityQueueB(["PriorityQueue"])
            end
        end


        subgraph Server["API Server<br/>[REST API]"]
        end
    end

    Datastore[("SQL database<br/> [datastore]")]
```

* The `Scheduler` system implements multiple `schedulers` per organisation.
  Per organisation there is a `boefje` and `normalizer` scheduler. With their
  respective priority queues. These queues are persisted in a SQL database.

#### Dataflows

Following we review how different dataflows, from the `boefjes` and the
`normalizers` are implemented within the `Scheduler` system. The following
events within a KAT installation will trigger dataflows in the `Scheduler`.
With the current implementation of the scheduler we identify the creation of
two different type of jobs, `boefje` and `normalizer` jobs.

##### Creation of boefje jobs

For a `boefje` job the following events will trigger a dataflow procedure to be
executed and subsequently the creation of a `boefje` job.:

1. When a scan level is increased on an OOI (`schedulers.boefje.push_tasks_for_scan_profile_mutations`),
   this will get the priority of 2.

    * When scan level mutation occurred, the `Scheduler` system will get the
      scan profile mutation from the `RabbitMQ` system.

    * For the associated OOI of this scan profile mutation, the `Scheduler`
      system will get the enabled boefjes for this OOI. (`tasks = ooi * boefjes`)

    * For each enabled boefje, a `BoefjeTask` will be created and added to the
     `PriorityQueue` of the `BoefjeScheduler`. A `BoefjeTask` is an object
     with the correct specification for the task runner to execute a boefje.

    * Each task will be checked if it is:

        * `is_allowed_to_run()`

        * `is_task_running()`

        * `has_grace_period_passed()`

        * `is_item_on_queue_by_hash()`

    * The `BoefjeScheduler` will then create a `PrioritizedItem` and push it to
      the queue. The `PrioritizedItem` will contain the created `BoefjeTask`.
      Additionally the `BoefjeTask` will be added to the database
      (`post_push()`). And serves as a log of the tasks that have been
      queued/executed, and can be queried through the API.

    ```mermaid
    flowchart TB

        %% External services
        RabbitMQ["RabbitMQ<br/>[message broker]"]

        %% External services flow
        RabbitMQ--"Get scan profile mutations<br/>(scan level increase)"-->get_scan_profile_mutation

        %% Boefje flow
        get_scan_profile_mutation-->get_boefjes_for_ooi-->create_boefje_task-->push_item_to_queue
        push_item_to_queue-->post_push
        push_item_to_queue-->push
        push-->Datastore
        post_push-->Datastore

        subgraph Scheduler["SchedulerApp [system]"]

            subgraph BoefjeScheduler["BoefjeScheduler [class]"]
                subgraph BoefjePopulateQueue["populate_queue() [method]"]
                    subgraph ScanProfileMutations["push_tasks_for_scan_profile_mutations() [method]"]
                        get_scan_profile_mutation[["get_scan_profile_mutation()"]]
                        get_boefjes_for_ooi[["get_boefjes_for_ooi()"]]
                        create_boefje_task("Create BoefjeTasks for OOI and enabled Boefjes")
                        push_item_to_queue[["push_item_to_queue()"]]
                    end
                end

                push[["push()<br/><br/>Add PrioritizedItem to PriorityQueue"]]
                post_push[["post_push()<br/><br/>Add BoefjeTask to database"]]
            end

            Datastore[("SQL database<br/>[datastore]<br/>")]

        end
    ```

2. Rescheduling of oois (`schedulers.boefje.push_tasks_for_random_objects`). In
   order to fill up the queue and to enforce that we reschedule tasks. We
   continuously get a batch of random ooi's from octopoes
   (`get_random_objects`). The tasks of from these ooi's (`tasks = ooi * boefjes`)
   will get the priority that has been calculated by the ranker. At the moment
   a task will get the priority of 3, when 7 days have gone by (e.g. how longer
   it hasn't been running the higher the priority it will get). For everything
   before those 7 days it will scale the priority appropriately.

    * From Octopoes we get `n` random ooi's (`get_random_objects`)

    * For each OOI, the `Scheduler` will get the enabled boefjes for this OOI.
      (`tasks = ooi * boefjes`)

    * For each enabled boefje, a `BoefjeTask` will be created and added to the
     `PriorityQueue` of the `BoefjeScheduler`.

    * Each task will be checked if it is:

        * `is_allowed_to_run()`

        * `is_task_running()`

        * `has_grace_period_passed()`

        * `is_item_on_queue_by_hash()`

    * The `BoefjeScheduler` will then create a `PrioritizedItem` and push it to
      the queue. The `PrioritizedItem` will contain the created `BoefjeTask`.
      Additionally the `BoefjeTask` will be added to the database
      (`post_push()`). And serves as a log of the tasks that have been
      queued/executed, and can be queried through the API.

    ```mermaid
    flowchart TB

    %% External services
    Octopoes["Octopoes<br/>[graph database]"]

    %% External services flow
    Octopoes--"Get random OOI's"-->get_random_objects

    %% Boefje flow
    get_random_objects-->get_boefjes_for_ooi-->create_boefje_task-->push_item_to_queue
    push_item_to_queue-->post_push
    push_item_to_queue-->push
    push-->Datastore
    post_push-->Datastore

    subgraph Scheduler["SchedulerApp [system]"]

        subgraph BoefjeScheduler["BoefjeScheduler [class]"]
            subgraph BoefjePopulateQueue["populate_queue() [method]"]
                subgraph RandomObjects["push_tasks_for_random_objects() [method]"]
                    get_random_objects[["get_random_objects()"]]
                    get_boefjes_for_ooi[["get_boefjes_for_ooi()"]]
                    create_boefje_task("Create BoefjeTasks for OOI and enabled Boefjes")
                    push_item_to_queue[["push_item_to_queue()"]]
                end
            end

            push[["push()<br/><br/>Add PrioritizedItem to PriorityQueue"]]
            post_push[["post_push()<br/><br/>Add BoefjeTask to database"]]
        end

        Datastore[("SQL database<br/>[datastore]<br/>")]

    end
    ```

3. Scan jobs created by the user in Rocky (`server.push_queue`), these tasks
   will get the highest priority of 1.

   * Rocky will create a `BoefjeTask` that will be pushed directly to the
     specified queue.

   ```mermaid
   flowchart TB

    Rocky["Rocky<br/>[webapp]"]

    Rocky--"Create scan job<br/>HTTP POST"-->push_item_to_queue

    push_item_to_queue-->post_push
    push_item_to_queue-->push
    push-->Datastore
    post_push-->Datastore

    subgraph Scheduler["SchedulerApp [system]"]

        subgraph Server["Server [class]"]
            push_item_to_queue[["push_item_to_queue()"]]

        end

        subgraph BoefjeScheduler["BoefjeScheduler [class]"]
            push[["push()<br/><br/>Add PrioritizedItem to PriorityQueue"]]
            post_push[["post_push()<br/><br/>Add BoefjeTask to database"]]
        end

        Datastore[("SQL database<br/>[datastore]<br/>")]

    end
   ```

4. When a plugin of type `boefje` is enabled or disabled in Rocky. This is
   triggered when the plugin cache of an organisation is flushed.

   * The cache of the organisation will be flushed at a specified interval.

   * Due to the flushing of the cache we get a new list of enabled boefjes for
     an organisation.
     (`connectors.services.katalogus._flush_organisations_boefje_type_cache()`)

   * New tasks will be created for enabled boefjes, when the OOIs are being
     rescheduled. This is then done when the `push_tasks_for_random_objects()`
     method is called.

##### Creation of normalizer jobs

For a `normalizer` job the following events will trigger a dataflow procedure

1. When a raw file is created (`schedulers.normalizer.create_tasks_for_raw_data`)

    * The `NormalizerScheduler` retrieves raw files that have been created in
      Bytes from a message queue.

    * For every mime type of the raw file, the `NormalizerScheduler` will
      retrieve the enabled normalizers for this mime type.
      (`create_tasks_for_raw_data()`)

    * For every enabled normalizer, a `NormalizerTask` will be created and
      added to the `PriorityQueue` of the `NormalizerScheduler`.

#### C4 Code level (Condensed class diagram)

The following diagram we can explore the code level of the scheduler
application, and its class structure.

```mermaid
classDiagram

    class App {
        +AppContext ctx
        +Dict[str, ThreadRunner] threads
        +Dict[str, Scheduler] schedulers
        +Dict[str, Listener] listeners
        +Server server
        run()
    }

    class Scheduler {
        <<abstract>>
        +AppContext ctx
        +Dict[str, ThreadRunner] threads
        +PriorityQueue queue
        +Ranker ranker
        populate_queue()
        push_items_to_queue()
        push_item_to_queue()
        pop_item_from_queue()
        post_push()
        post_pop()
        run()
    }

    class PriorityQueue{
        <<abstract>>
        +PriorityQueueStore pq_store
        pop()
        push()
        peek()
        remove()
        empty()
        qsize()
        full()
        is_item_on_queue()
        get_p_item_by_identifier()
        create_hash()
        dict()
        _is_valid_item()
    }

    class PriorityQueueStore{
        +Datastore datastore
        pop()
        push()
        peek()
        update()
        remove()
        get()
        empty()
        qsize()
        get_item_by_hash()
        get_items_by_scheduler_id()
    }

    class Ranker {
        <<abstract>>
        +AppContext ctx
        rank()
    }


    class Listener {
        listen()
    }

    App --|> "many" Scheduler : Implements
    App --|> "many" Listener : Has

    Scheduler --|> "1" PriorityQueue : Has
    Scheduler --|> "1" Ranker : Has

    PriorityQueue --|> PriorityQueueStore: References
```

The following describes the main components of the scheduler application:

* `App` - The main application class, which is responsible for starting the
  schedulers. It also contains the server, which is responsible for handling
  the rest api requests. The `App` implements multiple `Scheduler` instances.
  The `run()` method starts the schedulers, the listeners, the monitors, and
  the server in threads. The `run()` method is the main thread of the
  application.

* `Scheduler` - And implementation of a `Scheduler` class is responsible for
  populating the queue with tasks. Contains has a `PriorityQueue` and a
  `Ranker`. The `run()` method starts the `populate_queue()` method, which
  fill up the queue with tasks. The `run()` method is run in a thread.

* `PriorityQueue` - The queue class, which is responsible for storing the
  tasks.

* `Ranker` - The ranker class, which is responsible for ranking the tasks,
  and can be called from the `Scheduler` class in order to rank the tasks.

* `Server` - The server class, which is responsible for handling the HTTP
  requests.
