"""Return qualified recorded-minute counts and refuse unsupported target conversions."""

from pathlib import Path
import argparse, csv, json

ROOT = Path(__file__).resolve().parents[1]


def describe(request, accounts):
    if not isinstance(request, dict):
        return dict(accepted=False, reason="INVALID_REQUEST")
    if request.get("measure") != "RECORDED_MINUTE_RATE":
        return dict(accepted=False, reason="UNSUPPORTED_MEASURE")
    if request.get("denominator") != "ELIGIBLE_COMPLETED_NONDIVERTED":
        return dict(accepted=False, reason="DENOMINATOR_MISMATCH")
    cutoff = request.get("cutoff")
    if type(cutoff) is not int or cutoff not in [14, 15, 16]:
        return dict(accepted=False, reason="UNPLANNED_CUTOFF")
    rows = [r for r in accounts if r["destination"] == request.get("destination")]
    if len(rows) != 1:
        return dict(accepted=False, reason="AIRPORT_NOT_ESTABLISHED")
    row = rows[0]
    denominator = int(row["eligible_records"])
    if denominator == 0:
        return dict(accepted=False, reason="NO_ELIGIBLE_DENOMINATOR")
    return dict(
        accepted=True,
        destination=row["destination"],
        cutoff_minutes=cutoff,
        numerator=int(row["count_ge" + str(cutoff)]),
        denominator=denominator,
        rate_fraction=row["rate_ge" + str(cutoff)],
        source_unit="eligible current reporting-carrier source records",
        physical_seconds_known=False,
        European_equivalence_known=False,
    )


def run(out):
    with (out / "airport_accounts.csv").open(encoding="utf-8", newline="") as f:
        accounts = list(csv.DictReader(f))
    inputs = json.loads((ROOT / "data/exercise_inputs.json").read_bytes())
    output = [dict(request=r, result=describe(r, accounts)) for r in inputs]
    (out / "exercise.json").write_bytes((json.dumps(output, indent=2) + "\n").encode())
    print(
        json.dumps(
            dict(
                examples=len(output),
                accepted=sum(r["result"]["accepted"] for r in output),
            )
        )
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=ROOT / "results")
    run(p.parse_args().out)
