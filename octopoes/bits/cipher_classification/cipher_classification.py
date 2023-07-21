import csv
from pathlib import Path
from typing import Iterator, List, Tuple

from octopoes.models import OOI
from octopoes.models.ooi.findings import Finding, KATFindingType
from octopoes.models.ooi.service import SSLCipher


def get_severity_and_reasons(cipher_suite) -> List[Tuple[str, str]]:
    with Path.open(Path(__file__).parent / "List-ciphers-openssl-with-finding-type.csv", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        data = [{k.strip(): v.strip() for k, v in row.items()} for row in reader]

    # Filter the data for the provided cipher suite
    cipher_suite_data = [row for row in data if row["\ufeffCipher suite"] == cipher_suite]

    # If the cipher suite is not found, return an empty list
    if not cipher_suite_data:
        return [("Recommendation", "Unknown cipher")]

    # Columns that contain severities
    severity_cols = [col for col in data[0] if "Severity" in col]

    # Columns that contain reasons
    reason_cols = [col for col in data[0] if "Title" in col]

    severities_and_reasons = []
    for row in cipher_suite_data:
        for severity_col, reason_col in zip(severity_cols, reason_cols):
            # Check if there's a severity rating and a reason in the row
            if row[severity_col] and row[reason_col]:
                # Append the severity and reason as a tuple to the list
                severities_and_reasons.append((row[severity_col], row[reason_col]))

    return severities_and_reasons


def get_highest_severity_and_all_reasons(cipher_suite) -> Tuple[str, str]:
    # Define severity levels
    severity_levels = {"Critical": 3, "Medium": 2, "Recommendation": 1}

    # Get severities and reasons
    severities_and_reasons = get_severity_and_reasons(cipher_suite)

    if not severities_and_reasons:
        return "", ""

    # Initialize highest severity and corresponding reasons
    highest_severity_level = 0
    highest_severity = ""
    all_reasons = []

    for severity, reason in severities_and_reasons:
        # Update highest severity level and reasons if a higher severity level is found
        if severity_levels.get(severity, 0) > highest_severity_level:
            highest_severity_level = severity_levels.get(severity, 0)
            highest_severity = severity
        # Add all reasons to the list
        all_reasons.append(reason)

    # Join all reasons into a single string, separated by newlines
    all_reasons_str = "\n".join(all_reasons)

    return highest_severity, all_reasons_str


def run(input_ooi: SSLCipher, additional_oois, config) -> Iterator[OOI]:
    # Get the highest severity and all reasons for the cipher suite
    highest_severity, all_reasons = get_highest_severity_and_all_reasons(input_ooi.suite)

    # If no severity is found, return an empty list
    if not highest_severity:
        return

    # If the highest severity is critical, return a finding
    if highest_severity == "Critical":
        ft = KATFindingType(
            id="KAT-CRITICAL-BAD-CIPHER",
        )
        yield ft
        yield Finding(
            finding_type=ft.reference,
            ooi=input_ooi.reference,
            description=f"This cipher suite should not be used because:\n{all_reasons}",
        )

    # If the highest severity is medium, return a finding
    if highest_severity == "Medium":
        ft = KATFindingType(
            id="KAT-MEDIUM-BAD-CIPHER",
        )
        yield ft
        yield Finding(
            finding_type=ft.reference,
            ooi=input_ooi.reference,
            description=f"This cipher suite should not be used because:\n{all_reasons}",
        )

    # If the highest severity is recommendation, return a finding
    if highest_severity == "Recommendation":
        ft = KATFindingType(
            id="KAT-RECOMMENDATION-BAD-CIPHER",
        )
        yield ft
        yield Finding(
            finding_type=ft.reference,
            ooi=input_ooi.reference,
            description=f"This cipher suite should not be used because:\n{all_reasons}",
        )
