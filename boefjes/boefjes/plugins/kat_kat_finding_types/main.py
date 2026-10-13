import json

GROUP_PATH = "boefjes/plugins/kat_kat_finding_types/kat_finding_type_groups.json"

FINDING_TYPE_PATH = "boefjes/plugins/kat_kat_finding_types/kat_finding_types.json"


def validate_groups(groups: dict, finding_types: dict) -> None:
    if not isinstance(groups, dict) or not isinstance(finding_types, dict):
        raise ValueError("Group registry and finding types must be JSON objects")
    for group_id, group in groups.items():
        if not isinstance(group, dict) or not isinstance(group.get("name"), str) or not group["name"].strip():
            raise ValueError(f"Invalid group definition for {group_id!r}")
        visited = {group_id}
        parent = group.get("parent")
        while parent is not None:
            if not isinstance(parent, str):
                raise ValueError(f"Invalid parent ID for group {group_id!r}")
            if parent not in groups:
                raise ValueError(f"Unknown parent {parent!r} for group {group_id!r}")
            if parent in visited:
                raise ValueError(f"Cycle in finding type group hierarchy at {group_id!r}")
            visited.add(parent)
            ancestor = groups[parent]
            if not isinstance(ancestor, dict):
                raise ValueError(f"Invalid group definition for {parent!r}")
            parent = ancestor.get("parent")
    for finding_id, finding in finding_types.items():
        if not isinstance(finding, dict):
            raise ValueError(f"Invalid finding type {finding_id!r}")
        membership = finding.get("groups", [])
        if not isinstance(membership, list) or any(not isinstance(g, str) or g not in groups for g in membership):
            raise ValueError(f"Invalid groups for finding type {finding_id!r}: {membership!r}")
        if len(membership) != len(set(membership)):
            raise ValueError(f"Duplicate groups for finding type {finding_id!r}")


def run(boefje_meta: dict) -> list[tuple[set, bytes | str]]:
    with open(FINDING_TYPE_PATH) as json_file:
        data = json.load(json_file)
        with open(GROUP_PATH) as group_file:
            groups = json.load(group_file)
        validate_groups(groups, data)
        return [(set(), json.dumps(data))]
