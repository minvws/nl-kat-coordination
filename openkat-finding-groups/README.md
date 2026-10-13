# OpenKAT Finding Type Groups — proposed migration kit

Target: `boefjes/boefjes/plugins/kat_kat_finding_types/kat_finding_types.json` at commit `96154c7acc22b2fcfede9e8bab800a450bd2c12f`.

This is **not yet an integrated OpenKAT feature**. It provides group definitions, a conservative migration script and validation. The existing OpenKAT importer, Octopoes FindingType model, API and Rocky UI are **not modified**.

## Usage

Put `kat_finding_type_groups.json` next to the existing JSON file (or keep it with this script), then run:

```bash
python migrate_finding_types.py /path/to/kat_finding_types.json --output /tmp/kat_finding_types.grouped.json
python migrate_finding_types.py /tmp/kat_finding_types.grouped.json --check
```

The migration never overwrites its input and leaves unrecognized entries ungrouped. Review assignments manually, particularly where one keyword could indicate multiple topics. Existing fields and IDs are preserved; JSON formatting will be normalized. To assign a group manually, add `"groups": ["http-security-headers"]` to an entry. To create custom groups, edit the group registry and reference its stable ID.

## Integration needed for runtime support

1. Decide whether `groups` is imported into the `FindingType` OOI as a list of stable string IDs or resolved by a separate API. Do not assume unknown JSON fields survive the current importer.
2. Add group-registry loading and validation to the relevant importer/configuration layer.
3. Extend the FindingType serialization/model only if groups must be available through Octopoes.
4. Add UI grouping/filtering after the data contract is implemented.
5. Keep IDs stable to support future `FindingTypeGroup` OOIs and migration.

This kit deliberately does not rename existing Finding Type IDs, alter severity or claim to fix inaccurate descriptions. It also does not add scanner detections: new Finding Types require corresponding Bit logic.
