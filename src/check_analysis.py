"""Reconstruct every threshold and denominator with independent SQL/Fraction controls."""

from pathlib import Path
from datetime import date
from fractions import Fraction
import csv, json, sqlite3

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    with (ROOT / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main():
    n = 0

    def require(ok, label):
        nonlocal n
        assert ok, label
        n += 1

    db = sqlite3.connect(":memory:")
    db.execute(
        "CREATE TABLE cells(day TEXT,dest TEXT,carrier TEXT,category TEXT,can TEXT,div TEXT,delay TEXT,ind TEXT,n INTEGER)"
    )
    db.executemany(
        "INSERT INTO cells VALUES (?,?,?,?,?,?,?,?,?)",
        [
            (
                r["day"],
                r["destination"],
                r["carrier_id"],
                r["category"],
                r["cancelled_flag"],
                r["diverted_flag"],
                r["delay_token"],
                r["official_indicator"],
                int(r["records"]),
            )
            for r in read("data/day_carrier_cells.csv")
        ],
    )
    db.execute("CREATE INDEX cell_scope ON cells(dest,day,carrier)")
    db.create_function(
        "at_least",
        2,
        lambda value, cutoff: int(Fraction(value) >= cutoff) if value else 0,
    )
    category_fields = {
        "missing_key_records": "MISSING_KEY",
        "duplicate_key_records": "DUPLICATE_KEY",
        "unknown_operation_flag_records": "UNKNOWN_OPERATION_FLAGS",
        "both_operation_flags_records": "BOTH_OPERATION_FLAGS",
        "cancelled_records": "CANCELLED",
        "diverted_records": "DIVERTED",
        "unknown_delay_records": "UNKNOWN_DELAY",
        "eligible_records": "ELIGIBLE",
    }

    def reconstruct(where, args):
        def count(condition="1"):
            return db.execute(
                "SELECT COALESCE(SUM(n),0) FROM cells WHERE "
                + where
                + " AND ("
                + condition
                + ")",
                args,
            ).fetchone()[0]

        out = dict(source_records=count())
        for field, category in category_fields.items():
            out[field] = count("category='" + category + "'")
        out["raw_cancelled_flag_records"] = count("can='1'")
        out["raw_diverted_flag_records"] = count("div='1'")
        out["official_indicator_known"] = count(
            "category='ELIGIBLE' AND ind IN ('0','1')"
        )
        out["official_indicator_unknown"] = (
            out["eligible_records"] - out["official_indicator_known"]
        )
        out["official_indicator_positive"] = count("category='ELIGIBLE' AND ind='1'")
        out["official_indicator_mismatch"] = count(
            "category='ELIGIBLE' AND ind IN ('0','1') AND CAST(ind AS INTEGER)!=at_least(delay,15)"
        )
        for cutoff in [14, 15, 16]:
            number = count(
                "category='ELIGIBLE' AND at_least(delay," + str(cutoff) + ")"
            )
            out["count_ge" + str(cutoff)] = number
            out["rate_ge" + str(cutoff)] = (
                str(Fraction(number, out["eligible_records"]))
                if out["eligible_records"]
                else ""
            )
        out["count_14_to_15"] = out["count_ge14"] - out["count_ge15"]
        out["count_15_to_16"] = out["count_ge15"] - out["count_ge16"]
        out["boundary_fraction"] = (
            str(Fraction(out["count_15_to_16"], out["eligible_records"]))
            if out["eligible_records"]
            else ""
        )
        out["boundary_fraction_of_ge15"] = (
            str(Fraction(out["count_15_to_16"], out["count_ge15"]))
            if out["count_ge15"]
            else ""
        )
        require(
            sum(out[k] for k in category_fields) == out["source_records"],
            "complete independent eligibility partition",
        )
        return out

    catalog = json.loads((ROOT / "data/source_catalog.json").read_bytes())
    rebuilt = {}
    case_counts = {}
    for scope, file, keys, expected_keys in [
        (
            "AIRPORT",
            "airport_accounts.csv",
            ["destination"],
            {(d,) for d in ["ORD", "ATL"]},
        ),
        (
            "AIRPORT_DAY",
            "daily_accounts.csv",
            ["destination", "day"],
            {
                (d, date(2024, 1, k).isoformat())
                for d in ["ORD", "ATL"]
                for k in range(1, 32)
            },
        ),
        (
            "AIRPORT_CARRIER",
            "carrier_accounts.csv",
            ["destination", "carrier_id"],
            {(d, c) for d in ["ORD", "ATL"] for c in catalog["carrier_codes"]},
        ),
    ]:
        rows = read("results/" + file)
        observed = {tuple(r[k] for k in keys): r for r in rows}
        require(
            len(rows) == len(observed) and set(observed) == expected_keys,
            "complete fixed case set " + scope,
        )
        case_counts[scope] = len(rows)
        for key, row in observed.items():
            columns = {"destination": "dest", "day": "day", "carrier_id": "carrier"}
            where = " AND ".join(columns[k] + "=?" for k in keys)
            controls = reconstruct(where, key)
            for name, value in controls.items():
                require(
                    row[name] == str(value),
                    ("exact complete account", scope, key, name),
                )
            if scope == "AIRPORT_CARRIER":
                require(
                    row["carrier_codes"] == ";".join(catalog["carrier_codes"][key[1]]),
                    "complete carrier-code labels",
                )
            rebuilt[(scope, *key)] = controls
    actual = read("results/threshold_cases.csv")
    expected = {}
    for key, control in rebuilt.items():
        scope, dest, *extra = key
        day = extra[0] if scope == "AIRPORT_DAY" else ""
        carrier = extra[0] if scope == "AIRPORT_CARRIER" else ""
        for cutoff in [14, 15, 16]:
            expected[(scope, dest, day, carrier, str(cutoff))] = (
                str(control["eligible_records"]),
                str(control["count_ge" + str(cutoff)]),
                control["rate_ge" + str(cutoff)],
            )
    require(len(actual) == len(expected), "all threshold cases")
    seen = set()
    for row in actual:
        key = tuple(
            row[k]
            for k in ["scope", "destination", "day", "carrier_id", "cutoff_minutes"]
        )
        require(key in expected and key not in seen, "unique fixed threshold case")
        seen.add(key)
        require(
            tuple(
                row[k] for k in ["eligible_records", "label_positive", "rate_fraction"]
            )
            == expected[key],
            "exact numerator/denominator/rate",
        )
    summary = json.loads((ROOT / "results/summary.json").read_bytes())
    projection = json.loads((ROOT / "data/projection_receipt.json").read_bytes())
    headlines = dict(
        national_source_records=projection["national_records"],
        selected_source_records=projection["selected_records"],
        sufficient_cells=len(read("data/day_carrier_cells.csv")),
        airports=2,
        airport_days=62,
        airport_carrier_cases=case_counts["AIRPORT_CARRIER"],
        threshold_cases=len(expected),
        eligible_records=sum(
            rebuilt[("AIRPORT", d)]["eligible_records"] for d in ["ORD", "ATL"]
        ),
        boundary_records=sum(
            rebuilt[("AIRPORT", d)]["count_15_to_16"] for d in ["ORD", "ATL"]
        ),
        official_indicator_mismatches=sum(
            rebuilt[("AIRPORT", d)]["official_indicator_mismatch"]
            for d in ["ORD", "ATL"]
        ),
    )
    for name, value in headlines.items():
        require(summary[name] == value, "source-bound headline " + name)
    require(
        summary["original_cross_region_transfer"] == "UNEXECUTED"
        and summary["physical_seconds"] == summary["European_rate"] == "UNESTABLISHED",
        "original scope boundaries",
    )
    inputs = json.loads((ROOT / "data/exercise_inputs.json").read_bytes())
    exercise = json.loads((ROOT / "results/exercise.json").read_bytes())
    require(len(inputs) == len(exercise) == 7, "seven complete source-backed requests")
    for i, (request, output) in enumerate(zip(inputs, exercise)):
        require(request == output["request"], "complete request retained")
        answer = output["result"]
        accept = i in [0, 1]
        require(answer["accepted"] == accept, "independent request expectation")
        if accept:
            controls = rebuilt[("AIRPORT", request["destination"])]
            cutoff = request["cutoff"]
            require(
                answer["numerator"] == controls["count_ge" + str(cutoff)]
                and answer["denominator"] == controls["eligible_records"],
                "actual exercise source counts",
            )
            require(
                answer["rate_fraction"] == controls["rate_ge" + str(cutoff)],
                "actual exercise exact ratio",
            )
            require(
                answer["physical_seconds_known"] is False
                and answer["European_equivalence_known"] is False,
                "actual exercise qualifications",
            )
        else:
            require(
                answer["reason"]
                == ("AIRPORT_NOT_ESTABLISHED" if i == 6 else "UNSUPPORTED_MEASURE"),
                "unsupported interpretations rejected",
            )
    receipt = dict(
        status="PASS",
        finite_conditions=n,
        complete_accounts=sum(case_counts.values()),
        threshold_cases=len(actual),
        examples=7,
        methods="Independent SQLite weighted predicates and exact Fraction arithmetic;complete airport/day/carrier sets;no production metric or exercise imports.",
        scope="Current source counts and fixed recorded-label comparisons,not universal correctness,physical seconds or cross-region calibration.",
    )
    (ROOT / "results/independent_check.json").write_bytes(
        (json.dumps(receipt, indent=2) + "\n").encode()
    )
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
