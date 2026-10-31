"""Execute complete frozen airport/day/carrier accounts and fixed threshold probes."""

from pathlib import Path
from datetime import date
import argparse, csv, json
from metrics import account

ROOT = Path(__file__).resolve().parents[1]


def run(out):
    with (ROOT / "data/day_carrier_cells.csv").open(encoding="utf-8", newline="") as f:
        cells = list(csv.DictReader(f))
    catalog = json.loads((ROOT / "data/source_catalog.json").read_bytes())
    airports = []
    daily = []
    carriers = []
    thresholds = []
    for destination in ["ORD", "ATL"]:
        selected = [r for r in cells if r["destination"] == destination]
        airports.append(dict(destination=destination, **account(selected)))
        for day in range(1, 32):
            token = date(2024, 1, day).isoformat()
            daily.append(
                dict(
                    destination=destination,
                    day=token,
                    **account([r for r in selected if r["day"] == token])
                )
            )
        for carrier, codes in catalog["carrier_codes"].items():
            carriers.append(
                dict(
                    destination=destination,
                    carrier_id=carrier,
                    carrier_codes=";".join(codes),
                    **account([r for r in selected if r["carrier_id"] == carrier])
                )
            )
    for scope, rows in [
        ("AIRPORT", airports),
        ("AIRPORT_DAY", daily),
        ("AIRPORT_CARRIER", carriers),
    ]:
        for row in rows:
            for cutoff in [14, 15, 16]:
                thresholds.append(
                    dict(
                        scope=scope,
                        destination=row["destination"],
                        day=row.get("day", ""),
                        carrier_id=row.get("carrier_id", ""),
                        cutoff_minutes=cutoff,
                        eligible_records=row["eligible_records"],
                        label_positive=row["count_ge" + str(cutoff)],
                        rate_fraction=row["rate_ge" + str(cutoff)],
                    )
                )
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in [
        ("airport_accounts.csv", airports),
        ("daily_accounts.csv", daily),
        ("carrier_accounts.csv", carriers),
        ("threshold_cases.csv", thresholds),
    ]:
        with (out / name).open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    projection = json.loads((ROOT / "data/projection_receipt.json").read_bytes())
    summary = dict(
        national_source_records=projection["national_records"],
        selected_source_records=projection["selected_records"],
        sufficient_cells=len(cells),
        airports=len(airports),
        airport_days=len(daily),
        airport_carrier_cases=len(carriers),
        threshold_cases=len(thresholds),
        eligible_records=sum(r["eligible_records"] for r in airports),
        boundary_records=sum(r["count_15_to_16"] for r in airports),
        official_indicator_mismatches=sum(
            r["official_indicator_mismatch"] for r in airports
        ),
        original_cross_region_transfer="UNEXECUTED",
        physical_seconds="UNESTABLISHED",
        European_rate="UNESTABLISHED",
        qualification="One current reporting-carrier source month,two fixed destination codes;recorded-minute sensitivity,not physical-second or Europe-matched target conversion.",
    )
    (out / "summary.json").write_bytes((json.dumps(summary, indent=2) + "\n").encode())
    print(json.dumps(summary))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=ROOT / "results")
    run(p.parse_args().out)
