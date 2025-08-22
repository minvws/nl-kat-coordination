---
authors: Donny Peeters <@donnype>
state: draft
discussion:
labels: Frontend, Organizations, Scalability
---

# RFD 0008: Creating New Views

## Introduction

Many parts of OpenKAT are focussed on one organization only.
With our current scalability goals, i.e. scaling to thousands of organizations,
we need to make the interface multi-organization-friendly.
This means seeing and editing data over multiple organizations at the same time.

## Proposal

This proposal suggests a strategic approach for creating the new views for OpenKAT 2.0.
To make sure we build multi-organization-friendly views, we should first build the global views for all organizations.
Because filtering the information down for a selection of organizations,
or even just one organization, will likely boil down to changing the querysets on most views,
creating organization-specific views would require more work.
If we immediately build both views,
we would be spending twice the amount of time creating new pages with little-added benefit for an MVP.
Moreover, as filtering down on organizations is something we are going to do for many pages,
there is likely a useful abstraction we could introduce.
And we've all learned over time that abstractions should only be introduced once it covers a lot of instances.
In short, we should build our main views globally and then come up with a smart way to scope the information.

### Functional Requirements (FR)

1. As a User, I want to be able to see and modify information globally for my OpenKAT install
2. As a User, I want to be able to manage information for one organization or a selection of organizations

### Extensibility (Potential Future Requirements)

1. As a User, I want to be able to manage organizations filtered on a specific organization tag
