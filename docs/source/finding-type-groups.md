# Finding Type groups

The static OpenKAT Finding Type catalog defines `groups` as an array of stable group identifiers.
The canonical group registry is `boefjes/boefjes/plugins/kat_kat_finding_types/finding_type_groups.json`.
Each group has a display name, description, and optional parent identifier.
A Finding Type may belong to multiple groups. A parent relationship describes the taxonomy;
it does **not** imply descendant-aware filtering.

Run `python boefjes/boefjes/plugins/kat_kat_finding_types/validate_groups.py`
to validate group references and hierarchy.
Group propagation into Octopoes is provided by Phase 2; filtering in Rocky is separate work.

## Finding Type tags

Finding Types may additionally define an optional `tags` array of strings. Tags
are cross-cutting labels rather than security-domain groups; no tag OOI or tag
registry is required. The initial tag, `misconfiguration`, marks configuration
weaknesses across groups such as DNS Security, HTTP Security Headers, and HTTP
Cookies. An absent `tags` field means no tags.

The catalog validator also checks that provided tags are non-empty strings with
no duplicates. `KATFindingType` stores both `groups` and `tags`, using empty
lists for older definitions without these fields. Tags do not change finding
identity or severity. Filtering and dashboard persistence are separate Rocky
work in the next phase.
