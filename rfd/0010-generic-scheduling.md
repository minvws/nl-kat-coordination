---
authors: Donny Peeters <@donnype>
state: draft
discussion:
labels: Data Models, Scheduling
---

# RFD 0010: Generic Scheduling

## Introduction

In RFD 0005, an improved model for schedules and tasks was introduced,
with a focus on the relation between tasks and files.
Here, the only field that defines when a schedule should run is `schedule` that supports only cron expressions,
and the only field defining the input of a task is `data` that is modeled after a `BoefjeMeta` or `NormalizerMeta`.
In light of RFD 0006, 0007 and 0009, the schedule model in RFD 0005 does not suffice anymore:
- We want to make the arbitrary JSON data more explicit. Plugins can be run on a variety of input sets,
  so e.g. a BoefjeMeta is too limited as well as redundant: fields such as `started_at` and `ended_at` should be defined
  on the Task, while fields as `input_ooi` should be replaced by a more generic input data field on the Schedule.
- Schedules on an interval should be configured with a recurrence field, as discussed multiple times.
- We could want to trigger a plugin to parse a file when it is created, e.g. because it contains `nmap` output. This is
  also a schedule in the sense that it signals a plugin to start on a specific input set. In V1 of OpenKAT, 
  the trigger always equaled the input set: when we create a Hostname, we only get this hostname as input, nothing more.
  In OpenKAT V2, we can support arbitrary triggers and inputs, like triggering a plugin that checks for a newly created
  hostname if there was ever an IP address that had an open database port in the past that now points to this hostname.
  In one step, without bits.

## Proposal (WIP)

The core of this proposal is to:

1. Replace the `schedule` field with a `recurrences` field 
2. Drop the `data` and `type` field

3. Add a `plugins` field containing django_ql, that points to the plugin to run when the schedule is triggered.
4. Add a nullable `input` field containing django_ql, that generates the input data the plugin should run on.
   Perhaps we need a query per OOI type here, as djangoql assumes we know the model being queried.
5. Add a `run_on` field that will hold a type such as "file" or "hostname"
6. Add a `operation` field that specifies the operation such as "create", "update" or "delete",
   that only has effect if `run_on` is set.


This means that our current default daily scheduling boils down to about three database entries (pseudocode):
```json
[
  {
    "recurrences": "daily",
    "plugins": "recurrences = None",
    "input": {
      "hostname": "scan_level > 0",
      "ip_address": "scan_level > 0"
    },
    "run_on": null,
    "operation": null
  },
  {
    "recurrences": null,
    "plugins": "'{hostname}' in oci_arguments or '{hostname|ip_address}' in oci_arguments",
    "input": {},
    "run_on": "hostname",
    "operation": "created"
  },
  {
    "recurrences": null,
    "plugins": "'{ip_address}' in oci_arguments or '{hostname|ip_address}' in oci_arguments",
    "input": {},
    "run_on": "ip_address",
    "operation": "created"
  }
]
```
The first takes all plugins that have not defined their own `recurrences` and applies them to all IPV4Address and 
Hostname objects. We first check if the plugins are enabled, match scan levels and input, type and do as much as 
possible in parallel, of course.

The power here is that users can decide to have complete control where needed:

```json
[
  {
    "recurrences": "daily",
    "plugins": "recurrences = None and plugin_id not in ('bgp-download', 'rpki-download')",
    "input": {
      "hostname": "scan_level > 0",
      "ip_address": "scan_level > 0"
    }
  },
  {
    "recurrences": "hourly",
    "plugins": "plugin_id in ('bgp-download', 'rpki-download')",
    "input": {}
  },
  {
    "recurrences": "hourly",
    "plugins": "plugin_id  = 'kat_rpki_normalize2' ",
    "input": {}
  }
]
```

### Functional Requirements (FR)

1.

### Extensibility (Potential Future Requirements)

1.

### Why the proposal covers the requirements

- **FR 1**: 

- **EX 1**: 
