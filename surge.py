import ipaddress
from pathlib import Path

INPUT_DIR = Path(__file__).parent / "icp_domain_list"
OUTPUT_DIR = Path(__file__).parent / "domain_set"
TRACK_DIR = Path(__file__).parent / "track"
SURGE_DIR = TRACK_DIR / "surge"
SURGE_SUFFIX = ".list"
DOMAIN_SET_PREFIX = (
    r"https://raw.giteeusercontent.com/sredtfyguhijoikm/icp2rule/"
    r"raw/master/domain_set"
)


def is_ip(value: str) -> bool:
    """Check if the string is an IP address (IPv4 or IPv6)."""
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def to_ascii_domain(domain: str) -> str:
    """Convert an IDN domain to ASCII Punycode if needed.

    Uses Python's built-in IDNA codec (RFC 3490/5891).
    """
    return domain.encode("idna").decode("ascii")


def transform_domain(domain: str) -> str:
    """Transform a domain for Surge rules.

    - IDN domains: convert to Punycode ASCII
    - IP addresses: keep as-is
    - Regular domains: prepend a '.'
    """
    domain = domain.strip()
    assert domain, "Empty domain after strip"

    # Convert IDN (e.g. example.com) to Punycode (xn--...)
    domain = to_ascii_domain(domain)

    if is_ip(domain):
        return domain

    # Regular domain: prepend '.'
    return f".{domain}"


def process_list_file(filepath: Path) -> None:
    results: list[str] = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(maxsplit=1)
            assert len(parts) == 2, f"Malformed line in {filepath.name}: {line!r}"
            domain = parts[1]
            results.append(transform_domain(domain))

    output_path = OUTPUT_DIR / filepath.name
    with open(output_path, "w", encoding="utf-8") as f:
        for item in results:
            f.write(item + "\n")


def process_domain_sets() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    list_files = sorted(INPUT_DIR.glob("*.list"))
    if not list_files:
        print("No .list files found in icp_domain_list/")
        return

    print(f"Processing {len(list_files)} domain list file(s)...")
    for fp in list_files:
        process_list_file(fp)


def parse_track_line(line: str) -> tuple[str, str] | None:
    """Parse a track line into (label, domain_set_name).

    Columns are tab-separated. A line with only one column has no label.
    Blank lines and Markdown headings are ignored.
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    parts = [part.strip() for part in line.split("\t") if part.strip()]
    if not parts:
        return None
    if len(parts) == 1:
        return "", parts[0]
    return parts[0], parts[1]


def build_domain_set_rule(label: str, domain_set_name: str) -> str:
    name = domain_set_name.strip()
    if name.endswith(".list"):
        name = name.removesuffix(".list")

    rule = f"DOMAIN-SET,{DOMAIN_SET_PREFIX}/{name}.list"
    if label:
        rule += f"    // {label}"
    return rule


def process_track_file(filepath: Path) -> None:
    rules: list[str] = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        for line_number, line in enumerate(f, start=1):
            parsed = parse_track_line(line)
            if parsed is None:
                continue

            label, domain_set_name = parsed
            if not domain_set_name:
                raise ValueError(
                    f"Missing domain set name in {filepath.name}:{line_number}"
                )
            rules.append(build_domain_set_rule(label, domain_set_name))

    output_path = SURGE_DIR / f"{filepath.stem}{SURGE_SUFFIX}"
    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(f"{rule}\n" for rule in rules)
    print(f"  [OK] {output_path.name} ({len(rules)} rules)")


def process_track_files() -> None:
    SURGE_DIR.mkdir(parents=True, exist_ok=True)

    md_files = sorted(TRACK_DIR.glob("*.md"))
    if not md_files:
        print("No .md files found in track/")
        return

    print(f"Processing {len(md_files)} track file(s)...")
    for fp in md_files:
        process_track_file(fp)


def main() -> None:
    process_domain_sets()
    process_track_files()
    print("Done.")


if __name__ == "__main__":
    main()
