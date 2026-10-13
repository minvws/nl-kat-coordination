# Patch 2 reconciled candidate — not yet repository verified

This is a **candidate file overlay**, not a Git patch. It is based on the supplied Patch 2 archive and Patch 1 reviewed registry. Do not overwrite repository files without checking `git diff` against your actual branch.

- Retains Patch 1 descriptive group definitions, including `availability`.
- Adds `ipv6` and `internet-standards` from Patch 2 (18 group IDs total).
- Preserves Patch 2 assignments to 86 Finding Types and backend/model/test changes.
- Strengthens importer validation for malformed parents and duplicate group memberships.
- Includes Patch 1 migration utility and samples under `tools/finding_type_groups/`.

**Outstanding:** The Patch 2 Finding Type JSON cannot be verified against the current repository baseline from these archives alone. In particular, preservation of all pre-existing fields is not yet established. The migration utility uses heuristic rules that may differ from Patch 2's manually assigned groups. Avoid rerunning it on the already grouped catalog. Check actual OpenKAT pre-commit and integration tests in the repository environment.
