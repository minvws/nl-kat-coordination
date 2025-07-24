---
authors: Donny Peeters <@donnype>
state: discussion
discussion:
labels: Data Models, Katalogus, Boefjes, Normalizers, Bits
---

# RFD 0006: The KATalogus Database Schema

## Introduction

In light of RFD 0004 (OpenKAT 2.0), one of the components we should revise is the KATalogus database schema. In OpenKAT
V1, the KATalogus is a separate service that keeps track of the plugins that are available.

The current (integrated) model is as follows:

```mermaid
classDiagram
  class katalogus_boefje {
    plugin_id
    created
    static
    name
    description
    scan_level
    consumes
    produces
    jsonb schema
    cron
    interval
    run_on
    oci_image
    oci_arguments
    version
    id
  }
  class katalogus_boefjeconfig {
    settings
    enabled
    boefje_id
    organization_id
    id
  }
  class katalogus_normalizer {
    plugin_id
    created
    static
    name
    description
    consumes
    produces
    version
    id
  }
  class katalogus_normalizerconfig {
    settings
    enabled
    normalizer_id
    organization_id
    id
  }

  katalogus_boefjeconfig --> katalogus_boefje
  katalogus_boefjeconfig --> tools_organization
  katalogus_normalizerconfig --> katalogus_normalizer
  katalogus_normalizerconfig --> tools_organization
```

## Proposal

The core of this proposal is to:

1. As per RFD 0004, merge the KATalogus models into the OpenKAT schema.
2. Resolve the long-standing conflict between boefjes and normalizers by merging them into a Plugin model.
3. Make creating your own plugins even simpler by revising the `consumes` vs. `produces` architecture.
4. Improve the plugin configuration setup/definitions.

A discussion around the OCI images is postponed to a subsequent RFD, so those considerations are ignored in this
document.

See the proposed model below:

```mermaid
classDiagram
  class katalogus_plugin {
    id
    plugin_id
    name
    version
    settings_schema
    scan_level
    description
    consumes
    oci_image NULL
    oci_arguments
    created_at
  }

  class katalogus_pluginsettings {
    id
    settings
    plugin_id
    organizations
  }

  class katalogus_pluginenabled {
    id
    enabled
    plugin_id
    organization
  }

  katalogus_pluginconfig --> katalogus_plugin
  katalogus_pluginconfig --> tools_organization
  tools_organization --> katalogus_pluginconfig
  katalogus_pluginenabled --> tools_organization 
```

### Functional Requirements (FR)

With respect to plugin management:

1. Users should be able to enable/disable plugins and configure them per organization and globally.
2. Plugin versions should be pinned, and we should update them automatically instead of providing a "latest" option.
3. Users should be able to trigger plugins on demand for one or more organizations on one or more input oois.
4. Users should be able to schedule plugins periodically for one or more organizations on one or more input oois.

With respect to a discussion about the existence of the boefje-normalizer-bit relationship:

5. Some plugins should only run in containers and perhaps not be allowed to directly create OOIs.
6. We need to be able to do attribution of OOIs through plugins properly.
7. Maybe we shouldn't allow all plugins to write models to the database.

### Extensibility (Potential Future Requirements)

#### Related to the Plugins themselves

1. Perhaps plugin configuration should be manageable for a selection of organizations as well.
2. We should be able to import multiple plugins at once from external repositories

#### Related to scanning in general

3. Normalizers should be allowed to run on multiple raw files
4. One Boefje should be able to run on multiple OOIs
5. One Boefje should be able to run on multiple OOIs of different object_types
6. Normalizers should be able to use other OOIs as input as well
7. Bits should be able to query the database directly arbitrarily (Nibbles use-case partly)
8. Combining RawFiles and OOIs to create Findings should be possible

### A Generic Plugin Model (FR 1,2,3,4)

Functional Requirement 1 and 2 can be tackled with the new variant of the original model using the same logic.
We do need to make sure versions are pinned upon creation, something to touch upon for an RFD on the OCI images.

For Functional Requirement 3 and 4, the current model already allows for configuring or scheduling plugins for
arbitrary organizations. For plugins to allow for multiple input oois, we should tackle the plugin interface and
figure out the impact on deletion propagation. Details on a new boefje interface and improvements on the scheduler
will be discussed in separate RFDs. The suggested model is still an MVP in light of these requirements

### Don't we Need Separate Models? Boefjes? Normalizers? (FR 5,6,7)

#### Current limitations

Right now there is a clear separation between boefjes and normalizers:

- Boefjes run on 1 input OOI and produces RawFiles
- Normalizers run on 1 RawFile and produces only OOIs
- Bits run on 1 input OOI, but can have several parameters, and output OOIs

And:

- The output of Normalizers for the same Boefje overwrites the previous output and deletes what hasn't been found
  anymore.
- Boefjes/normalizers run per organization
- Boefjes should run in containers as much as possible because these could run in untrusted environments and/or run
  untrusted code.
- Normalizers conceptually should not have to talk to the internet and are hence "pure functions".

However, these are mostly **implementation details**. Arguments for this split would mostly be about:

- Clear separation of untrusted tasks doing scans versus pure functions parsing data (FR 5).
- The attribution is conceptually always the same (FR 6,7).

But actually, this makes it almost impossible to implement the Extensibility Requirements 3 to 8 currently, or at least
without a lot of work.

In short, the current structure is too rigid, and our old database model does not allow to differ from the structure.
Moreover, this structure makes implementing features such as creating your own scans significantly more work as you
always need to define two tasks (boefje & normalizer).
And the input/outputs are forced into the `OOI --Boefje--> Raw --Normalizer--> OOI`.

#### Why a Generic Plugin Model Also Tackles These Use-cases (And More)

Let's break down why the new simplified model still covers each requirement:

- **FR 5**: This is quite trivial: only plugins that have the `oci_image` field set should run in a container.
- **FR 6**: "Properly" is vague, but if one plugin's Task uses the RawFile of another plugin, this is relatively
  easy to query if you know your SQL: join in the RawFile and its related TaskResults and Task for all tasks and you
  have a tree-like structure on top of your table.
- **FR 7**: Currently we do not have any mechanism to stop boefje output to be parsed, and we are not running
  untrusted boefjes yet, so we might categorize this as a nice-to-have. But it would be straightforward to add a
  boolean field to the current model to mark a plugin as untrusted and require subsequent plugins with more rights
  to parse its output.

Moreover, this would allow us to tackle more of the Extensibility Requirements:

- **Ex 3**: If we allow tasks to pull in arbitrary RawFiles or define multiple RawFiles as their input, this is
  definitely possible as we are not restricted to the old plugin flow.
- **Ex 4**: The same holds for this requirement.
- **Ex 4**: And this one. We should simply update the way the `consumes` field works and improve the boefje signatures.
- **Ex 6**: As long as the attribution is logged properly, because we only look at the output data we don't care
  what sources were used once we fix deletion propagation.
- **Ex 7**: When we move to XTDB 2.0, we can implement a lot of Bits (hopefully) as `UPDATE WHERE` statements doing
  arbitrary operations on the data. Again, not restricting the input but generating a well-defined output makes this
  possible
- **Ex 8**: This would just be a consequence of Ex 3 and 6.
