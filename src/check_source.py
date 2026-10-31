"""Check complete native-bound saved sufficient cells without redownloading sources."""

from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime
from fractions import Fraction
import csv, hashlib, json

ROOT = Path(__file__).resolve().parents[1]


def main():
    n = 0

    def require(ok, label):
        nonlocal n
        assert ok, label
        n += 1

    native = json.loads((ROOT / "data/native_verification.json").read_bytes())
    require(native["status"] == "PASS", "independent native source receipt")
    for name, digest in native["hashes"].items():
        require(
            hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest,
            "native-bound bytes",
        )
    projection = json.loads((ROOT / "data/projection_receipt.json").read_bytes())
    catalog = json.loads((ROOT / "data/source_catalog.json").read_bytes())
    with (ROOT / "data/day_carrier_cells.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    require(
        len(rows) == native["sufficient_cells"] == projection["sufficient_cells"],
        "all sufficient cells",
    )
    require(
        sum(int(r["records"]) for r in rows)
        == native["selected_records"]
        == projection["selected_records"],
        "all selected native records",
    )
    require(
        native["national_records"] == projection["national_records"],
        "complete national count control",
    )
    signatures = set()
    codes = defaultdict(set)
    for row in rows:
        require(int(row["records"]) > 0, "positive source cell count")
        require(row["destination"] in ["ORD", "ATL"], "fixed destination")
        require(
            datetime.strptime(row["day"], "%Y-%m-%d").year == 2024
            and row["day"].startswith("2024-01-"),
            "fixed month and strict source date",
        )
        require(
            row["category"]
            in [
                "MISSING_KEY",
                "DUPLICATE_KEY",
                "UNKNOWN_OPERATION_FLAGS",
                "BOTH_OPERATION_FLAGS",
                "CANCELLED",
                "DIVERTED",
                "UNKNOWN_DELAY",
                "ELIGIBLE",
            ],
            "explicit eligibility",
        )
        require(
            row["official_indicator"] in ["0", "1", "MISSING", "INVALID"],
            "official indicator preserved",
        )
        require(
            row["cancelled_flag"] in ["0", "1", "MISSING", "INVALID"]
            and row["diverted_flag"] in ["0", "1", "MISSING", "INVALID"],
            "operation flags preserved",
        )
        if row["delay_state"] == "FINITE":
            Fraction(row["delay_token"])
            require(bool(row["delay_token"]), "finite exact recorded delay")
        else:
            require(
                row["delay_state"] in ["MISSING", "INVALID", "NONFINITE"]
                and row["delay_token"] == "",
                "unknown delay not zero",
            )
        if row["category"] == "ELIGIBLE":
            require(
                row["cancelled_flag"] == row["diverted_flag"] == "0"
                and row["delay_state"] == "FINITE",
                "eligible denominator definition",
            )
        signature = tuple(v for k, v in row.items() if k != "records")
        require(signature not in signatures, "unique sufficient cell")
        signatures.add(signature)
        codes[row["carrier_id"]].add(row["carrier_code"])
    require(
        {k: sorted(v) for k, v in codes.items()} == catalog["carrier_codes"],
        "complete carrier labels",
    )
    print(
        json.dumps(
            dict(
                status="PASS",
                finite_conditions=n,
                sufficient_cells=len(rows),
                selected_records=native["selected_records"],
                scope="Saved native-bound source counts,identity of sufficient cells,explicit eligibility and provenance;not new native reacquisition.",
            )
        )
    )


if __name__ == "__main__":
    main()
