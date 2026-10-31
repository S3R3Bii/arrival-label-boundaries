"""Independently verify used manuscript values, complete tables and reviewed scope."""

from pathlib import Path
from decimal import Decimal, localcontext
from fractions import Fraction
import csv, hashlib, json, re, unicodedata
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    if name.endswith(".csv"):
        with (ROOT / name).open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    return json.loads((ROOT / name).read_bytes())


def expected(binding):
    value = load(binding["file"])
    if binding["query"] is not None:
        matched = [
            r for r in value if all(r[k] == v for k, v in binding["query"].items())
        ]
        assert len(matched) == 1
        value = matched[0]
    for key in binding["field"] or []:
        value = value[key]
    op = binding["operation"]
    if op == "length":
        return str(len(value))
    if op == "commas":
        return format(int(value), ",")
    if op in ["percent2", "percent3"]:
        exact = Fraction(value) * 100
        with localcontext() as context:
            context.prec = 80
            return format(
                Decimal(exact.numerator) / Decimal(exact.denominator),
                "." + op[-1] + "f",
            )
    assert op == "value"
    return str(value)


def main():
    n = 0

    def require(ok, label):
        nonlocal n
        assert ok, label
        n += 1

    pdf = PdfReader(ROOT / "paper/manuscript.pdf")
    require(len(pdf.pages) == 6, "six current pages")
    pages = [unicodedata.normalize("NFKC", p.extract_text() or "") for p in pdf.pages]
    compact = re.sub(r"\s+", " ", "\n".join(pages))
    words = re.sub(r"([A-Za-z])-\s+([A-Za-z])", r"\1\2", "\n".join(pages))
    words = re.sub(r"\s+", " ", words)
    tex = (ROOT / "paper/main.tex").read_text(encoding="utf-8")
    bindings = load("paper/bindings.json")
    require(
        len(bindings) > 60 and len({b["name"] for b in bindings}) == len(bindings),
        "unique actual bindings",
    )
    for binding in bindings:
        value = expected(binding)
        require(value == binding["display"], "independent source value and format")
        require(
            "\\newcommand{\\" + binding["name"] + "}{" + value + "}" in tex,
            "actual definition",
        )
        require(
            len(re.findall(r"\\" + re.escape(binding["name"]) + r"\b", tex)) >= 2,
            "actually used beyond definition",
        )
        require(value in compact, "actual PDF value")
    table = re.sub(r"\s+", " ", pages[1])
    rows = load("results/airport_accounts.csv")
    require(
        [r["destination"] for r in rows] == ["ORD", "ATL"], "complete fixed airports"
    )
    fields = [
        ("All selected source records", "source_records"),
        ("Eligible completed nondiverted", "eligible_records"),
        ("Missing key", "missing_key_records"),
        ("Duplicate key", "duplicate_key_records"),
        ("Unknown operation flags", "unknown_operation_flag_records"),
        ("Both operation flags set", "both_operation_flags_records"),
        ("Cancelled", "cancelled_records"),
        ("Diverted", "diverted_records"),
        ("Unknown delay", "unknown_delay_records"),
        ("Usable official indicator among eligible", "official_indicator_known"),
        ("Unknown official indicator among eligible", "official_indicator_unknown"),
        ("Official indicator mismatch among eligible", "official_indicator_mismatch"),
    ]
    for label, field in fields:
        require(
            label + " " + " ".join(format(int(r[field]), ",") for r in rows) in table,
            "complete source account row",
        )
    for cutoff in [14, 15, 16]:
        require(
            "Recorded delay >= "
            + str(cutoff)
            + " Positive count "
            + " ".join(format(int(r["count_ge" + str(cutoff)]), ",") for r in rows)
            in table,
            "complete threshold count row",
        )
        values = [
            expected(
                dict(
                    file="results/airport_accounts.csv",
                    query={"destination": r["destination"]},
                    field=["rate_ge" + str(cutoff)],
                    operation="percent2",
                )
            )
            + "%"
            for r in rows
        ]
        require(
            "Percent of eligible " + " ".join(values) in table,
            "complete threshold rate row",
        )
    for phrase in [
        "Not peer reviewed",
        "original US-to-Europe model-transfer study remains unexecuted",
        "source informed, not blinded",
        "Source values were visible",
        "not an immutable original-vintage capture",
        "not endorsed by DOT/BTS",
        "Azure optimization",
        "zero denominator is unavailable",
        "No European source values are transformed or scored",
        "not a reconstruction of a European rate or physical-second lateness",
    ]:
        require(phrase.lower() in words.lower(), ("actual qualification", phrase))
    require(len(load("PLAN_FREEZE.json")["hashes"]) == 26, "26 protected dependencies")
    verification = load("results/verification.json")
    require(verification["authored_fixture_methods"] == 29, "29 authored fixtures")
    for name, digest in verification["result_sha256"].items():
        require(
            hashlib.sha256((ROOT / "results" / name).read_bytes()).hexdigest()
            == digest,
            "current output bytes",
        )
    for suffix in ["310", "312"]:
        replay = load("results/reproduction_cpython" + suffix + ".json")
        require(
            replay["status"] == "PASS" and replay["full_history"],
            "isolated full history",
        )
        require(
            len(replay["reproduced_files"]) == 6
            and replay["unchanged_source_files"] == 10,
            "actual replay scope",
        )
        require(
            replay["reproduced_files"] == list(verification["result_sha256"]),
            "six outputs",
        )
    scope = load("paper/PUBLICATION_SCOPE.json")
    require(
        scope["scope"] == "independent-program-study"
        and scope["formal_submission_target"] is False,
        "independent publication scope",
    )
    require(len(scope["public_files"]) == 5, "five scoped files")
    for name, digest in scope["public_files"].items():
        require(
            hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest,
            "current scoped bytes",
        )
    for name in ["threshold_rates", "daily_boundary", "source_denominators"]:
        require(
            (ROOT / "figures" / (name + ".pdf")).read_bytes()
            == (ROOT / "paper/images" / (name + ".pdf")).read_bytes(),
            "current figure copy",
        )
    visual = load("paper/visual_review.json")
    require(visual["pages_reviewed"] == [1, 2, 3, 4, 5, 6], "all pages reviewed")
    require(
        visual["manuscript_sha256"]
        == hashlib.sha256((ROOT / "paper/manuscript.pdf").read_bytes()).hexdigest(),
        "reviewed PDF bytes",
    )
    for name, digest in visual["reviewed_figure_png_sha256"].items():
        require(
            hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest,
            "reviewed figure bytes",
        )
    receipt = dict(
        status="PASS",
        finite_conditions=n,
        used_numeric_bindings=len(bindings),
        pages=len(pdf.pages),
        scope_files=5,
        scope="Used source bindings, complete PDF tables, current output and figure hashes, two replay receipts, all rendered pages and approved independent publication scope. Finite evidence, not universal correctness.",
    )
    (ROOT / "paper/verification.json").write_bytes(
        (json.dumps(receipt, indent=2) + "\n").encode()
    )
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
