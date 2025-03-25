---
authors: Jeroen Dekkers (@dekkers )
state: draft
discussion: https://github.com/minvws/nl-kat-coordination/pull/4051
labels: boefjes
---

# RFD 0004: Deduplication of boefjes between organization

The goal of deduplication of boefjes is to avoid doing multiple scans in similar
organizations for the same assets. When a large number of organizations have the
same asset this would prevent scanning the asset too many times and save
resources.

## Functional requirements

Deduplication can only be done when the input of the boefje is exactly the same.
This includes all the boefje settings. A few boefjes need to have the
organization, so those boefjes can't be duplicated.

When doing deduplication between organizations it would be possible for a user
to see that a boefje task for a certain OOI was already done for an organization
in the same KAT install earlier while the user might not have access to this
organization. This might be a problem for certain usage of OpenKAT, so
deduplication should be a setting that can be turned off.

Usage of previous raw files can also only be used if they are not older than the
requested interval in the requesting organization.

## Nonfunctional requirements

The primary goal is currently to not run the same boefje again for a different
organization by reusing the raw file of the earlier boefje task. It is not clear
if we can easily prevent having to save the raw file again for the other
organization. Not saving again would be a nice to have for now and an
optimization we can do later.

## Technical design

### Current situation

The current input of a boefje is defined as the BoefjeMeta. This currently defined as:

```python
class Job(BaseModel):
    id: UUID
    started_at: AwareDatetime | None = Field(default=None)
    ended_at: AwareDatetime | None = Field(default=None)

    @property
    def runtime(self) -> timedelta | None:
        if self.started_at is not None and self.ended_at is not None:
            return self.ended_at - self.started_at
        else:
            return None


class Boefje(BaseModel):
    """Identifier for Boefje in a BoefjeMeta"""

    id: Annotated[str, StringConstraints(min_length=1)]
    version: str | None = Field(default=None)


class BoefjeMeta(Job):
    boefje: Boefje
    input_ooi: str | None = None
    arguments: dict = {}
    organization: str
    runnable_hash: str | None = None
    environment: dict[str, str] | None = None
```

The local job handler currently get the `BoefjeMeta` object from the scheduler
and additionally sets `arguments["input"]`, `runnable_hash`, `environment`,
`started_at` fields (see `BoefjeHandler` in boefjes/job_handler.py). The local
boefje `run` function gets the full `BoefjeMeta` pydyantic object:

```python
from boefjes.job_models import BoefjeMeta

def run(boefje_meta: BoefjeMeta) -> list[tuple[set, bytes | str]]:
```

The docker runner create the boefje meta object itself and currently only sets
the `id`, `boefje`, `input_ooi`, `arguments`, `organization` and `environment` fields (see
`create_boefje_meta` in boefjes/api.py). The docker boefje `run` function gets a
dictionary with those values:

```python
def run(boefje_meta: dict) -> list[tuple[set, bytes | str]]:
```

### Arguments that are passed to boefjes that need to be considered for deduplication

To make sure we only do deduplication on boefje tasks that really are the same
we should be more strict to what we pass to the boefje as input. We've been
providing more information than is necessary to the boefjes by given the whole
BoefjeMeta as input to each boefje.

#### Usage of arguments field

This is used by almost every boefje and the main way to specify on what the
boefje should run. This is the serialized OOI, the result of calling `serialize`
on an OOI.

It might be better to provide the serialized OOI as `input_ooi` argument to the
boefje `run` to make it more clear what the contents of the field is, see below
for the proposed signature.

#### Usage of organization field

The external DB boefje currently needs the organization to fetch the data from
the external database. Obviously this means the boefje can't be deduplicated.

To support this we should add a flag to boefjes that require the organization.
If the flag is set, we provide organization to the boefje and can't do
deduplication. If the flag isn't set, we don't provide the organization and can
duplicate. This way we make sure the organization is never used when it is not
supposed to be.

#### Usage of boefje task id field

There is only one boefje that uses the task id. This

The log4j vulnerability is now over 3 years old.

For the sake of simplicity we might do away with passing the boefje the task id.

#### Usage of input_ooi field

Only the leakix boefje used the input_ooi field. For the sake of simplicy we
should probably not provide this to the boefje. It should be easy to refactor
this so it used the serialized input OOI.

#### Usage of environment field

This is not used directly from the BoefjeMeta argument in `run`, but the
provided variables are set environment variables are set and the boefje

#### Usage of started_at, endated_at, boefje and runnable_hash fields

This isn't used by any boefje and can be safely removed from the boefje arguments.

#### Boefje signature / arguments

Boefje that does not require organization can have the following signature:

```python
def run(input_ooi: dict[str, Any]) -> list[tuple[set, bytes | str]]:
```

And boefje that requires organization:

```python
def run(input_ooi: dict[str, Any], organization: str) -> list[tuple[set, bytes | str]]:
```

The `input_ooi` is the serialized input OOI that is stored in the BoefjeMeta
`arguments`. The environment field does need to be passed as argument because it
is already passed to the boefje using environment variables.

### Deduplication implementation

The scheduler is the place where boefjes are scheduled so that seems to be most
obvious place to implement deduplication. Because the data necessary is
currently spread out over multiple services / databases this means it would need
to do requests to other services to fetch this information. This is unavoidable
because there is currently no single place with all the information.

#### Whether boefje needs organization

The scheduler already fetches and caches all the available boefjes for an
organization, so the scheduler can use this data to easily check if the boefje
requires the organization and can't be deduplicated.

#### Environment settings from previous task in other organization

This data is stored in bytes and needs to be fetched by the scheduler to
determine whether the environment settings are the same.

#### Environment settings of to be deduplicated boefje task

This is a complicated. The scheduler can fetch the current configured
environment from the katalogus, but this is merged with the environment that is
passed directly to the boefje runner as environment variables. There is
currently no easy way to fetch those and adding an API for this to the boefje
runner doesn't seem to be a good idea.

The best course of action seems to be to disallow the environment variables
passed to the boefje runner when deduplication is turned on. If both
deduplication is turned on and environment variables are passed to the boefje
runner we need to return an error because the user needs to know that the passed
variables aren't used.

### Valid time

If we deduplicate boefje, we need to add the output which a certain valid time.
Using the current time doesn't seem right, because the boefje task was run
earlier. But using the earlier time means we need to create and object with an
older valid time which might complicate inference.

#### Deduplication algorithm option 1

A possible algorithm for deduplication could be:

- The scheduler wants to scheduler a boefje for a specific organization and
  input OOI.
- The scheduler checks if the boefje needs the organization. If so it can
  continu with scheduling the boefje task.
- The scheduler queries the stored tasks to see if a different organization has
  already run on this input OOI.
- If there is a match, the scheduler fetches the environment of the previous
  boefje task and the environment of the new boefje task. If they are the same
  they can be deduplicated. If they differ the new boefje needs to be scheduled.

This could be further optimized by storing information about the configured
boefje settings. If we store which organizations have the same settings and
which have different settings, we don't have to fetch this information for every
boefje task.

#### Deduplication algorithm option 2

The goal is of OpenKAT is to do continuous monitoring. This means that most of
the time we are scanning an already existing OOI. For deduplication this means
that the common scenario is that a certain OOI might in a large number of
organizations, the scenario that a new OOI is added that already exists in
another organization is probably less common.

We can take advantage of this by checking all other organizations for the same
OOIs either before or after a boefje has run. The big advantage of doing
deduplication this way is that the raw file has just been created and we don't
need to insert data from the past or insert data with a different valid date
than the date of the raw file.

A way to optimize this might be to mark whether an OOI also exists in a
different organization. This can be done when OOIs are created, updated and
deleted instead of doing that check on every boefje run. We might also do
something similar when environment settings are updated.

#### Implementation of algorithm 2

In the katalogus database we store a hash of the environment settings. We will
add an endpoint in the katalogus or change the existing endpoint so that mula
can fetch the boefje information together with the environment hashes for each
organization.

Mula will then add all the organizations to the task. The list of organizations
will then be passed to the boefje runner when the boefje runner requests tasks.
After the task is executed the boefje runner will save the raw files for all the
organizations.
