# Extending the scheduler functionality

Within the scheduler project you'll be able to extend the functionality with
your own procedures. The most likely customization you'll make will be
the directives of populating the queue, dispatching and ranking tasks.

Examples on how to extend the classes can be found in their respective folders.
The files are named `boefje.py`, and `normalizer.py` that are a specific KAT
implementations.

Helpful resources are: the directory structure from the `README.md` file and
the C4 Code level (Condensed class diagram) from the
[architecture](https://github.com/minvws/nl-kat-coordination/tree/main/mula/docs/architecture.md)
file.

## Populating the queue

We can subclass the `schedulers.Scheduler` class and implement our own `run()`
method. Because we have the `context.AppContext` as an attribute, we're able to
access shared data. In this case we can reference external services, such as
`Octopoes`, `Katalogus`, `Bytes`, etc. This can help us make fine-grained
decisions on what tasks you want to push on to the queue.

Take a look in the [`schedulers/`](schedulers/) folder for an example, how
this is implemented, and reference either the `boefje.py` or `normalizer.py`
file for the current implementation.

One example implementation could be that tasks are scheduled for at specific
time, or need to be put onto the queue at a specific time.

When you've defined your own schedulers, be sure to initialize and start them
from the `app.py` file.

## Ranking tasks

Again, we can subclass the `rankers.Ranker` class and implement our own ranker.
In this case we can implement the `rank` method. This expects the `obj`
argument of type `Any`. As you can inspect from the default implementations
in the [`rankers/`](rankers/) folder in either the `boefje.py` or `normalizer.py`
file, the `obj` can be any object that can help you determine what rank or
priority the task should have on the priority queue.

Additionally, you'll have access to the `context.AppContext` object, which
allows you to reference additional information in order to make your own
ranking algorithm.
