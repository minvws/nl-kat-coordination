#!/usr/bin/env python3
"""Add optional group IDs to OpenKAT's Finding Type JSON, without changing existing fields.

Usage: python migrate_finding_types.py path/to/kat_finding_types.json --output /tmp/kat_finding_types.grouped.json
Review all assignments before committing. Run with --check to validate an existing grouped file.
"""

import argparse
import json
import logging
import re
from pathlib import Path

GROUPS_FILE = Path(__file__).with_name("kat_finding_type_groups.json")
logger = logging.getLogger(__name__)

# Conservative rules: review results before merging; unmatched types remain ungrouped.
RULES = [
    (
        r"HSTS|CONTENT.SECURITY.POLICY|\bCSP\b|X.FRAME.OPTIONS|X.CONTENT.TYPE.OPTIONS|"
        r"REFERRER.POLICY|PERMISSIONS.POLICY|EXPECT.CT|X.DNS.PREFETCH|SECURITY.HEADER",
        "http-security-headers",
    ),
    (r"COOKIE|SAMESITE|HTTPONLY", "http-cookies"),
    (r"TLS|SSL|CERTIFICATE|CIPHER|HTTPS", "tls-certificates"),
    (r"DMARC|DKIM|SPF|STARTTLS|SMTP|MAIL|MX.RECORD|DANE|MTA.STS|TLS.RPT", "email-security"),
    (r"DNSSEC|DNS|CAA.RECORD|ZONE.TRANSFER", "dns-security"),
    (r"OPEN.PORT|DATABASE.PORT|RDP|VNC|SSH|TELNET|PORT.EXPOSED|NETWORK", "network-exposure"),
    (r"\bCVE\b|VULNERABILIT|\bCVSS\b", "known-vulnerabilities"),
    (r"OUTDATED|END.OF.LIFE|\bEOL\b|SOFTWARE.UPDATE|UNSUPPORTED.SOFTWARE", "software-security"),
    (
        r"EXPOSED.FILE|DIRECTORY.LIST|GIT.DIRECTORY|BACKUP.FILE|STACK.TRACE|"
        r"INFORMATION.DISCLOSURE|VERSION.DISCLOSURE",
        "information-disclosure",
    ),
    (r"AUTHENTICATION|AUTHORIZATION|PASSWORD|LOGIN|ACCESS.CONTROL", "authentication"),
    (r"CLOUD|S3.BUCKET|KUBERNETES|DOCKER|CONTAINER", "cloud-infrastructure"),
    (r"PRIVACY|TRACKING|PERSONAL.DATA|GREEN.HOSTING", "privacy"),
    (r"IPV6|AVAILABILITY|UNREACHABLE|DOWNTIME", "availability"),
    (r"HTTP|WEBSITE|WEB.SERVER|NIKTO", "http-exposure"),
]


def load(path):
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique_pairs)


def validate(groups, findings):
    errors = []
    if not isinstance(groups, dict) or not isinstance(findings, dict):
        raise ValueError("Both JSON roots must be objects")
    for gid, group in groups.items():
        if not isinstance(group, dict) or not isinstance(group.get("name"), str) or not group["name"].strip():
            errors.append(f"{gid}: invalid group name")
            continue
        parent = group.get("parent")
        if parent is not None and not isinstance(parent, str):
            errors.append(f"{gid}: parent must be a group ID or null")
            continue
        if parent is not None and parent not in groups:
            errors.append(f"{gid}: unknown parent {parent}")
            continue
        visited = {gid}
        while parent is not None and parent in groups and parent not in visited:
            visited.add(parent)
            ancestor = groups[parent]
            if not isinstance(ancestor, dict):
                errors.append(f"{gid}: invalid parent definition {parent}")
                break
            parent = ancestor.get("parent")
            if parent is not None and not isinstance(parent, str):
                errors.append(f"{gid}: invalid parent ID in chain")
                break
        if parent in visited:
            errors.append(f"{gid}: cycle in parent chain")
    for fid, item in findings.items():
        if not isinstance(item, dict):
            errors.append(f"{fid}: Finding Type must be an object")
            continue
        assigned = item.get("groups", [])
        if not isinstance(assigned, list) or any(not isinstance(g, str) for g in assigned):
            errors.append(f"{fid}: groups must be an array of IDs")
            continue
        if len(assigned) != len(set(assigned)):
            errors.append(f"{fid}: duplicate group assignment")
        for group in assigned:
            if group not in groups:
                errors.append(f"{fid}: unknown group {group}")
    return errors


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", type=Path)
    p.add_argument("--output", type=Path, help="New output file (never overwrites input)")
    p.add_argument("--check", action="store_true", help="Validate only")
    args = p.parse_args()
    groups = load(GROUPS_FILE)
    findings = load(args.input)
    if not args.check:
        if args.output is None or args.output.resolve() == args.input.resolve():
            p.error("Provide --output different from the input file")
        if args.output.exists():
            p.error("Output exists; refusing to overwrite")
        count = 0
        for fid, item in findings.items():
            if not isinstance(item, dict) or "groups" in item:
                continue
            searchable = f"{fid} {item.get('name', '')}".upper()
            for pattern, group in RULES:
                if re.search(pattern, searchable):
                    item["groups"] = [group]
                    count += 1
                    break
        grouped = sum(bool(item.get("groups")) for item in findings.values() if isinstance(item, dict))
        logger.info("Assigned groups to %s entries; %s remain ungrouped.", count, len(findings) - grouped)
    errors = validate(groups, findings)
    if errors:
        for error in errors:
            logger.error("%s", error)
        raise SystemExit(1)
    if args.check:
        logger.info("OK: %s Finding Types and %s groups validated.", len(findings), len(groups))
    else:
        args.output.write_text(json.dumps(findings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        logger.info("Wrote %s (review automatic classifications before committing).", args.output)


if __name__ == "__main__":
    main()
