# Finding Type groups

The static OpenKAT Finding Type catalog defines `groups` as an array of stable group identifiers.
The canonical group registry is `boefjes/boefjes/plugins/kat_kat_finding_types/finding_type_groups.json`.
Each group has a display name, description, and optional parent identifier.
A Finding Type may belong to multiple groups. A parent relationship describes the taxonomy; it does **not** imply descendant-aware filtering.

Run `python boefjes/boefjes/plugins/kat_kat_finding_types/validate_groups.py` to validate group references and hierarchy.
This first phase only adds catalog metadata; propagation into Octopoes and filtering in Rocky are separate changes.
