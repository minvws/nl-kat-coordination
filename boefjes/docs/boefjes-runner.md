# Design for new boefjes runner

The new boefjes runner will run boefjes in a containerized environment. This
ensures isolation of code and dependencies, and allows for easy distribution
of boefjes outside the KAT repository and release cycle.

A boefje can be written in any language, as long as it follows the I/O contract
(see below) and it is properly packaged in an OCI image.

## Images

[OCI images][oci-spec] will be
used to package the boefjes' code, its dependencies (libraries) and required
tools such as Nmap.

[oci-spec]: https://github.com/opencontainers/image-spec/blob/main/spec.md

### Distribution

OCI images can be distributed in any OCI registry, such as Docker Hub or
GitHub Container Registry. Several open source projects are available to
create a self-hosted OCI registry, such as [Harbor][harbor].

The boefje can be imported into the katalogus using its OCI image URL. It can
be pinned to a version-specific tag, SHA256 identifier, or simply use the `latest`
tag.

A JSON list of recommended boefjes will be included with each OpenKAT release,
or published to https://openkat.nl.

[harbor]: https://goharbor.io/

### Metadata

To import a boefje into the katalogus, we need some of its metadata. We can
distribute this metadata together with the image by leveraging the [OCI image
manifest][oci-manifest-spec]. For example, we could add an annotation to the
manifest with a well-known name and predefined format, such as JSON, or add
multiple annotations for each metadata attribute.

The essential metadata includes:
- Name
- Version
- Description
- Image URL
- Settings schema
- List of OOI types that the boefje works on
- Boefjes runner HTTP API version
- Minimum compatible KAT version (for OOI schema compatibility)

[oci-manifest-spec]: https://github.com/opencontainers/image-spec/blob/main/manifest.md

## I/O

Because stdin and stdout in container orchestrators are relatively complicated
and work on a best-effort basis, this is not reliable enough for boefje input
and output. Instead, we use a simple HTTP API for input and output.

This HTTP API will be part of new boefjes runner and will communicate with
existing parts of KAT such as bytes and mula (the scheduler) to get the boefje
input and save its output.

The HTTP API will be versioned, so that the API can evolve while staying
compatible with existing boefjes.

### Input

The container will get a URL of an API endpoint that will provide its input as
one of its command line arguments. The container will then make a GET request
to this URL to get the input.

The input is a JSON object, specified by the following JSON schema:

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://openkat.nl/boefje_input.schema.json",
    "title": "Boefje input",
    "properties": {
        "task_id": {
            "type": "string"
        },
        "output_url": {
            "type": "string"
        },
        "boefje_meta": {
            "type": "object",
            "properties": {
                "boefje": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string"
                        },
                        "version": {
                            "type": "string"
                        }
                    }
                },
                "input_ooi": {
                    "type": "string"
                },
                "arguments": {
                    "type": "object"
                },
                "organization": {
                    "type": "string"
                },
                "environment": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "string"
                    }
                }
            }
        },
        "required": [
            "boefje",
            "input_ooi",
            "arguments",
            "organization",
            "environment"
        ]
    },
    "required": [
        "task_id",
        "output_url",
        "boefje_meta"
    ]
}
```

### Output

When the container is finished, it can POST its output to the URL specified in
the input JSON object. The output is a JSON object, specified by the following
JSON schema:

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://openkat.nl/boefje_output.schema.json",
    "title": "Boefje output",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["COMPLETED", "FAILED"]
        },
        "files": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string"
                    },
                    "content": {
                        "type": "string",
                        "contentEncoding": "base64"
                    },
                    "tags": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": ["content"]
            }
        }
    },
    "required": ["status"]
}
```

The tags for each file can include a MIME type.

## Logging

Logging will be captured through the container orchestrator/runtime's API and
stored in bytes. Alternatively, the boefje can output its own logging in a
separate file as part of its output, which will be stored in bytes as well.

## Runtimes

### Docker

Docker containers can be run as one-off jobs by creating a container, polling
its status on a regular interval, and removing it when it is finished.

An official, well-maintained Python API is available:
- https://pypi.org/project/docker/
- https://docker-py.readthedocs.io/en/stable/
- https://github.com/docker/docker-py

Logging can be captured through the API, but the specifics of available on the
logging driver: https://docs.docker.com/config/containers/logging/json-file/

### Kubernetes

Kubernetes has a specific object type for one-off workloads:
[Jobs](https://kubernetes.io/docs/concepts/workloads/controllers/job/).

These Jobs can be created through the Kubernetes API, and their status can be
polled (pull-based) or watched (push-based) through the API as well.

An official, well-maintained Python API is available:
- https://pypi.org/project/kubernetes/
- https://github.com/kubernetes-client/python

Logging can be captured [through the API][k8s-logs-api], but logs get rotated so
a large volume of logs may not be fully available. See
https://kubernetes.io/docs/concepts/cluster-administration/logging/ for more
details.

[k8s-logs-api]: https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.27/#read-log-pod-v1-core

### Nomad

Nomad can run one-off jobs by setting the job type to 'batch':
- https://developer.hashicorp.com/nomad/docs/job-specification/job#type
- https://developer.hashicorp.com/nomad/docs/schedulers#batch

An unofficial Python API is available:
- https://pypi.org/project/python-nomad/
- https://github.com/jrxfive/python-nomad

Logging can be captured [through the API][nomad-logs-api],
but Nomad does not retain logs for long periods of time. From
https://developer.hashicorp.com/nomad/tutorials/manage-jobs/jobs-accessing-logs:
> While the logs command works well for quickly accessing application logs, it
> generally does not scale to large systems or systems that produce a lot of log
> output, especially for the long-term storage of logs. Nomad's retention of log
> files is best effort, so chatty applications should use a better log retention
> strategy.

[nomad-logs-api]: https://developer.hashicorp.com/nomad/api-docs/client#stream-logs

## Limitations

In this design the boefjes runner will create a new container for each task,
which has a non-negligible overhead. This overhead can be reduced by batching
multiple tasks in a single container run. This design does not currently
consider that to ensure the implementation is as simple as possible. It can be
added to the runner in the future, but will also require changes to the KAT
scheduler to support scheduling batched tasks.
