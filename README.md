# OpenKAT Finding Type Groups + Misconfiguration Tags (proposed patch)

Apply the files at their matching repository paths. This builds on the previous Finding Type Groups patch and the uploaded OpenKAT source snapshot.

## Design

- Technical domain remains in `groups` (e.g. `http-security-headers`).
- Cross-cutting weakness category is stored in optional `tags` (currently only `misconfiguration`).
- `general-configuration` is a fallback group for future findings without a suitable technical domain; no existing findings were moved into it.
- Existing Finding Type IDs and six original descriptive fields remain intact.
- No new FindingTypeGroup OOI is introduced.
- Tags are carried into `KATFindingType` OOIs by the normalizer.

## Scope and limitations

Initial tagging is intentionally conservative (selected configuration weaknesses only); manual security review is needed before merging. The `ALLOWED_TAGS` set is deliberately small and can be expanded with an explicit taxonomy later. No Rocky UI filtering, dedicated tag registry, or live XTDB integration is included.

## Verification

Run `pytest boefjes/tests/plugins/test_kat_finding_types.py` from the OpenKAT environment with its project dependencies configured. Check importer behavior and Octopoes serialization in an integration environment.
