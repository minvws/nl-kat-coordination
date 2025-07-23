---
authors: Donny Peeters <@donnype>
state: draft
discussion:
labels: Octopoes, Origins
---

# RFD 0007: Deletion Propagation

## Introduction

Origins in OpenKAT have two functions. The first is to control deletion propagation:

- **Declarations** are "circular" origins with one OOI in the result set that equals the `ooi` (input) field, and
  are hence not subject to deletion propagation.
- **Observations** are regular origins because old items from their `result` (array) field will be deleted upon an
  update operation.
- **Affirmations** are Declarations that should actually be deleted, because they don't "prove" the OOI. An example
  of this is a job that only adds extra information to an OOI, and hence is circular without proving existence.
- **Inference Origins** are origins found by bits, and hence updates on OOIs with an Inference Origin or
  InferenceOrigins themselves trigger the run of the bit the origins references.

The second function is to provide attribution: an origin has a `method` (a.k.a. `normalizer_id` or `bit_id`),
`source_method` (a.k.a. `boefje_id`) and a `task_id` (a.k.a. `normalizer_meta_id`) field.
This means that origins can be used to:

1. Find the tasks that produced an OOI
2. Find all OOIs that were found in a certain Task
3. Find OOIs that were the result of a specific boefje, normalizer or bit.
4. Trigger bits on changes in an event-driven manner

## Proposal

The core of this proposal is to remove Origins: Declarations, Observations and Affirmations.
To still have deletion propagation, we should delete old OOIs in plugins explicitly when needed and define `CASCADE`s,
on our models. This would solve all deletion propagation requirements.

### (Draft) New Bit Trigger System

With XTDB 2.0, bits might be powerful enough to run them all every minute, especially if we would keep track of what
was already updated through an `updated_at` like field/feature. But this would make everything less responsive.
Hence, we could re-implement the trigger system using Django Signals and trigger bits on an UPDATE, CREATE or DELETE.

### (Draft) New attribution path towards OOIs

To still relate OOIs to Tasks, OOIs should get a new `attribution_id` string field that is either:

- A `task_id` pointing to a Task
- A `user_id'` pointing to a User that manually created the OOI
- Any future attribution identifiers

### Functional Requirements (FR)

1. As a User, I don't want duplicate OOIs in OpenKAT because it makes it hard to find the currently active OOIS and
   thereby act quickly.
2. As a User, I want data that is not valid anymore because a scan did not find it again to be removed.

### Extensibility (Potential Future Requirements)
