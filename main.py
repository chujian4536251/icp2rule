import json
from collections import defaultdict
from pathlib import Path

RAW_DIR = Path(__file__).parent / "raw_icp_result"
OUTPUT_DIR = Path(__file__).parent / "icp_domain_list"


def extract_suffix(service_licence: str) -> int:
    """Extract the numeric suffix from a serviceLicence string."""
    _, sep, suffix = service_licence.rpartition("-")
    assert sep, f"No '-' separator in: {service_licence!r}"
    assert suffix.isdigit(), f"Suffix not numeric in: {service_licence!r}"
    return int(suffix)


def resolve_name(unit_name: str, main_licence: str) -> str:
    """Pick the group name: unitName if >=6 chars, otherwise mainLicence."""
    if unit_name and len(unit_name) >= 6:
        return unit_name
    assert main_licence, (
        f"unitName too short and no mainLicence: unit_name={unit_name!r}"
    )
    return main_licence


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    json_files = sorted(RAW_DIR.glob("*.json"))
    if not json_files:
        print("No JSON files found in raw_icp_result/")
        return

    # Group all records by name (unitName or mainLicence), deduplicating by (serviceLicence, domain)
    groups: dict[str, set[tuple[str, str]]] = defaultdict(set)

    for fp in json_files:
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)

        for batch in data.get("result", []):
            for item in batch:
                domain = item.get("domain")
                licence = item.get("serviceLicence", "")
                unit_name = item.get("unitName", "")
                main_licence = item.get("mainLicence", "")
                assert domain, f"Missing domain in item: {item}"
                name = resolve_name(unit_name, main_licence)
                groups[name].add((licence, domain))

    if not groups:
        print("No records found.")
        return

    # Sort each group and write output
    for name, items in groups.items():
        sorted_items = sorted(items, key=lambda x: (extract_suffix(x[0]), x[1]))
        output_path = OUTPUT_DIR / f"{name}.list"
        with open(output_path, "w", encoding="utf-8") as f:
            f.writelines(f"{licence} {domain}\n" for licence, domain in sorted_items)
        print(f"  [OK] {name}.list ({len(sorted_items)} domains)")

    print(f"Done. {len(groups)} file(s) written.")


if __name__ == "__main__":
    main()
