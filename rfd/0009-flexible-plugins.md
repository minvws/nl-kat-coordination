---
authors: Donny Peeters <@donnype>
state: draft
discussion:
labels: Data Models, Plugins
---

# RFD 0006: Flexible (OCI) Plugins

## Introduction

Plugins are part of the core of OpenKAT.
They form the engine that continuously monitors important OOIs for Findings.
For both the community and experienced OpenKAT users,
being able to create, configure and extend plugins are perhaps the most important features we provide,
on the one hand because of the large open source community that provides vulnerability scanning scripts
and the fact that newly discovered threats need to be mitigated immediately,
and on the other hand because every organization is unique and needs tailored tooling as well to monitor their systems.

This means that managing plugins should be as easy as possible.
One big improvement has recently been to containerize all of our plugins (boefjes to be precise) by default.
This means that users can host an image that adheres to our specification remotely and add it to OpenKAT manually,
also see [this design document](https://github.com/minvws/nl-kat-coordination/blob/fb613fc6d0ee9c446d39e8326f04036997ad7e52/docs/source/developer-documentation/boefjes-runner.md).
Note that to consistently get data in and out of the ephemeral plugin containers,
as the document states, we are really bound to using an internal API.

However, it has become clear that this does not make creating plugin images trivial:
1. To reuse code that talks with our internal API for multiple images, we had to create an intermediate OCI image. 
2. We could not reuse the code for non-Python-images, requiring multiple implementations or a different base image.
3. Even for Python-based-images we needed to install extra requirements to talk to the API
4. We need to maintain multiple versions of these images for multiple versions of the API. This would mean that we 
   need to add extra upgrading logic on a release for older plugin versions and track which image supports which API 
   version. (This has caused bugs already for images that were not pinned.)
5. Adding even just a script as a new plugin meant creating, hosting and maintaining a whole new OCI image.

We also noticed that a lot of plugins started to boil down to starting a subprocess that called the native tool in the
container directly and return the output.

Moreover, we still cannot handle certain scenarios with the current boefje-normalizer-bit-structure:
1. It is not possible to trigger normalizers on two or more raw files
2. It is not possible to get other oois into a normalizer
3. It is not possible to run a boefje on multiple OOIs at once
4. It is not possible to normalize multiple raw files at once

But with the new schema from RFD 0006 and the level of control introduced in the design of RFD 0007,
it is possible to mitigate these limitations.

## Proposal

The core of this proposal is to:

1. As per RFD 0006, treat boefje and normalizers simply as _plugins_.
2. Allow plugins to talk to both file and object APIs, so they can gather the data they need themselves dynamically,
   instead of limiting this to a declarative definition of the input type (see the `consumes` field).
3. Create a binary that we can mount in any container as an entrypoint at runtime, that calls the cli command in the 
   `oci_arguments` field and sends the output (`stdout`) as a file to our internal API.
4. For any plugins that we do write custom code for, aim to normalizer data right away where possible. Files that 
   are needed for e.g. audit trailing can simply be sent to the API in the same task.
5. Scope what these ephemeral containers can access by creating a fine-grained authorization scheme: define before 
   starting the container what it should be allowed to access, and pass a token that has these rights attached to it 
   in the container that we can check in the API again once the container starts performing requests to the API.
6. As we still have the common path of running a boefje on one or multiple hostnames or IP addresses: provide a way 
   to pass these in the `oci_arguments` field using e.g. a template string such as `{hostname}`. For running 
   plugins on multiple objects we could consider mounting or fetching a file with hostnames or creating more intricate
   templating logic. This is however the second step and perhaps something to refine in another RFD.  


### Functional Requirements (FR)

1.

### Extensibility (Potential Future Requirements)

1.

#### Why the proposal covers the requirements

- **FR 1**: 

- **EX 1**: 
