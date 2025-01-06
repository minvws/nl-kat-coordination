---
authors: (@originalsouth)
state: draft
discussion: https://github.com/minvws/nl-kat-coordination/pull/4004
labels: hashing, pydantic, ooi, octopoes
---

# RFD 0003: OOI Hashing

## Background

The current `__hash__` implementation of OOI's:

https://github.com/minvws/nl-kat-coordination/blob/8730e188e9dad6276a363aaeaead8fc1deb82ac9/octopoes/octopoes/models/__init__.py#L242-L243

is broken because it only considers the primary key; meaning that OOI's with
fields _not_ recorded in the primary key are erroneously deemed to be the same
objects, causing Python's built-in hash dependent structures to find collisions.
Additionally, we'll have to consider whether we want for:

```python
d1 = {'a': 1, 'b': 2}
d2 = {'b': 2, 'a': 1}
```

to have different hashes (ie. `hash(d1) == hash(d2)` or `hash(d1) != hash(d2)`).
(this because python dicts are ordered)

## Proposal

Since we are dealing with OOI based on Pydantic BaseModel's we can easily
generate a dict of the object using `model_dump`. Assuming that this is the
best object to start to begin our `__hash__` implementation on, the question
becomes how to best hash a dict (as python still hasn't figured out how to do
this natively).

The natural question arises why not hash `model_dump_json`? Because there is no
guarantee it is stable see
https://github.com/pydantic/pydantic/discussions/10343.

## Evaluation

Hence, here I compare two algorithms with benchmarks:

1. hashing the ooi using the [`jcs`](https://pypi.org/project/jcs/) package
2. hashing the ooi using a custom `freeze()` function

Code:

```python
#!/usr/bin/env python

from typing import Iterable, Any
import jcs
import random
import string
import time

N = 8
MAX_DEPTH = 4
K = 10**6


def random_string():
    return ''.join(random.choice(string.ascii_letters) for _ in range(random.randint(1, N)))


def random_obj(depth: int = 0, k: int = 7) -> Any:
    if depth < MAX_DEPTH:
        rand_choice = random.randint(0, k)
        if rand_choice == 0:
            return random.random()  # float
        elif rand_choice == 1:
            return random.randint(0, 10**6)  # int
        elif rand_choice == 2:
            return random_string()  # string
        elif rand_choice == 3:
            return [random_obj(depth + 1, 2) for _ in range(random.randint(1, N))]  # list
        elif rand_choice == 4:
            return [random_obj(depth + 1, 2) for _ in range(random.randint(1, N))]  # list
            # Non JSON compatible so broken for hasher_2 but hasher_1 digests it
            # return {random_obj(depth + 1, 2) for _ in range(random.randint(1, N))}  # set
        else:
            return {random_string(): random_obj(depth + 1) for _ in range(random.randint(1, N))}  # dict[str, Any]
            # Non JSON compatible so broken for hasher_2 but hasher_1 digests it
            # return {random_obj(depth + 1, 2): random_obj(depth + 1) for _ in range(random.randint(1, N))}  # dict[Any, Any]
    else:
        return random_string()


targets = [random_obj() for _ in range(K)]


def hasher_1(obj: Any) -> int:
    def freeze(obj: Iterable[Any | Iterable[Any]]) -> Iterable[int]:
        if isinstance(obj, Iterable) and not isinstance(obj, (str, bytes)):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    yield hash(key)
                    yield from freeze(value)
            else:
                for item in obj:
                    yield from freeze(item)
        else:
            yield hash(obj)
    return hash(tuple(freeze(obj)))


def hasher_2(obj: Any) -> int:
    return hash(jcs.canonicalize(obj))


st = time.time_ns()
_ = list(map(hasher_1, targets))
dt = time.time_ns() - st

print(f"hasher_1: {dt / 10**9 / K}s")


st = time.time_ns()
_ = list(map(hasher_2, targets))
dt = time.time_ns() - st

print(f"hasher_2: {dt / 10**9 / K}s")
```

Resulting in:

```
hasher_1: 2.213041571e-05s
hasher_2: 3.159127834e-05s
```

## Determinations

Personally, I would opt for `hasher_1` as it more flexible and faster, but
`hasher_2` is easier to maintain; also open to other suggestions.

So how do we proceed to solve this problem?

## References

- [Issue #3808](https://github.com/minvws/nl-kat-coordination/issues/3808): has to be solved either in that branched or before that branch is merged.
- [Issue #4000](https://github.com/minvws/nl-kat-coordination/issues/4000): original issue and discussion
