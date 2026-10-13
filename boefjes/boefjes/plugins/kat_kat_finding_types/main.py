import json

GROUP_PATH = "boefjes/plugins/kat_kat_finding_types/kat_finding_type_groups.json"

FINDING_TYPE_PATH = "boefjes/plugins/kat_kat_finding_types/kat_finding_types.json"


ALLOWED_TAGS = {"misconfiguration"}


def validate_groups(groups: dict, finding_types: dict) -> None:
    for group_id, group in groups.items():
        parent = group.get("parent")
        if parent is not None and parent not in groups:
            raise ValueError(f"Unknown parent {parent!r} for group {group_id!r}")
        visited = {group_id}
        while parent is not None:
            if parent in visited:
                raise ValueError(f"Cycle in finding type group hierarchy at {group_id!r}")
            visited.add(parent)
            parent = groups[parent].get("parent")
    for finding_id, finding in finding_types.items():
        membership = finding.get("groups", [])
        if not isinstance(membership, list) or any(not isinstance(g, str) or g not in groups for g in membership):
            raise ValueError(f"Invalid groups for finding type {finding_id!r}: {membership!r}")
        tags = finding.get("tags", [])
        if (
            not isinstance(tags, list)
            or any(not isinstance(t, str) or t not in ALLOWED_TAGS for t in tags)
            or len(tags) != len(set(tags))
        ):
            raise ValueError(f"Invalid tags for finding type {finding_id!r}: {tags!r}")


def run(boefje_meta: dict) -> list[tuple[set, bytes | str]]:
    with open(FINDING_TYPE_PATH) as json_file:
        data = json.load(json_file)
        with open(GROUP_PATH) as group_file:
            groups = json.load(group_file)
        validate_groups(groups, data)
        return [(set(), json.dumps(data))]
