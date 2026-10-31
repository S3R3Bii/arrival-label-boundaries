"""Write a source-bound independent manuscript from complete recorded-label exports."""

from pathlib import Path
from decimal import Decimal, localcontext
from fractions import Fraction
import csv, json, shutil

ROOT = Path(__file__).resolve().parents[1]
bindings = []


def letters(index):
    result = ""
    while True:
        result = chr(65 + index % 26) + result
        index = index // 26 - 1
        if index < 0:
            return result


def load(file):
    if file.endswith(".csv"):
        with (ROOT / file).open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    return json.loads((ROOT / file).read_bytes())


def bind(file, field=None, query=None, operation="value"):
    value = load(file)
    if query is not None:
        found = [r for r in value if all(r[k] == v for k, v in query.items())]
        assert len(found) == 1
        value = found[0]
    for key in field or []:
        value = value[key]
    if operation == "length":
        value = len(value)
    if operation == "commas":
        display = format(int(value), ",")
    elif operation.startswith("percent"):
        exact = Fraction(value) * 100
        with localcontext() as context:
            context.prec = 80
            display = format(
                Decimal(exact.numerator) / Decimal(exact.denominator),
                "." + operation[-1] + "f",
            )
    else:
        display = str(value)
    name = "Bound" + letters(len(bindings))
    bindings.append(
        dict(
            name=name,
            file=file,
            field=field,
            query=query,
            operation=operation,
            display=display,
        )
    )
    return "\\" + name + "{}"


def headline(field):
    return bind("results/summary.json", [field], operation="commas")


def airport(code, field, op="commas"):
    return bind("results/airport_accounts.csv", [field], dict(destination=code), op)


def checked(field):
    return bind("results/verification.json", [field], operation="commas")


p1 = (
    r"""\documentclass[11pt,letterpaper]{article}
\usepackage[margin=.72in]{geometry}
\usepackage[T1]{fontenc}
\usepackage{lmodern,microtype,booktabs,array,graphicx,pdflscape,xcolor,amsmath,hyperref}
\hypersetup{colorlinks=true,urlcolor=blue,linkcolor=blue,pdftitle={Arrival-delay labels at the minute boundary}}
\setlength{\parindent}{0pt}\setlength{\parskip}{6pt}
\newcommand{\heading}[1]{\vspace{4pt}{\large\bfseries #1}\par}
%%BINDINGS%%
\begin{document}
{\LARGE\bfseries Arrival-delay labels at the minute boundary\par}
\vspace{5pt}
Independent research program\hfill 31 October 2026 UTC\\
\textit{Not peer reviewed. One current source view; fixed recorded-minute probes.}

\heading{Practical finding}
Changing a delay cutoff changes the target even when the flights stay the same. In the fixed January 2024 reporting-carrier cohort, """
    + headline("boundary_records")
    + r""" of """
    + headline("eligible_records")
    + r""" eligible records change labels between recorded cutoffs of 15 and 16 minutes.

At ORD the affected count is """
    + airport("ORD", "count_15_to_16")
    + r""" of """
    + airport("ORD", "eligible_records")
    + r""", a """
    + airport("ORD", "boundary_fraction", "percent3")
    + r""" percentage-point rate difference. At ATL it is """
    + airport("ATL", "count_15_to_16")
    + r""" of """
    + airport("ATL", "eligible_records")
    + r""", or """
    + airport("ATL", "boundary_fraction", "percent3")
    + r""" percentage points. These are sensitivity results on recorded minutes, not a reconstruction of a European rate or physical-second lateness.

\heading{Recommended use}
Keep the source field, numeric cutoff and eligible denominator with a benchmark label. Rebuild the label from supported source observations before pooling systems. Retain cancellation, diversion and unknown-field accounts alongside completed-flight rates. A matching label name or published aggregate is insufficient evidence that the target and population match.

The local implementation returns qualified recorded-minute counts and rejects unsupported requests to infer physical seconds, European OTP15, safety rankings or a transfer score. This is a runnable implementation exercise, not a deployed forecasting service or measured operating benefit.

\heading{Source and fixed scope}
The official BTS January 2024 reporting-carrier archive contains """
    + headline("national_source_records")
    + r""" national rows. Every arrival to the two fixed destination codes is retained: """
    + headline("selected_source_records")
    + r""" records in """
    + headline("sufficient_cells")
    + r""" day/carrier/source-state count cells. Native archives and flight identities remain private.

The public protocol fixed month, destinations, eligibility and cutoffs before flight-record retrieval. After the source form failed, the official archive directory supplied a published direct link to the identical fixed file. That transport change was committed before reading its body. The earlier failure is preserved; no month, airport or reporting-population substitution was made.

\heading{Original transfer question remains unexecuted}
The original US-to-Europe model-transfer study remains unexecuted. Common-event, reporting-population, source-rights and historical-vintage requirements remain unresolved. The 16-minute probe is an authored comparison on US recorded values. It does not equate US minutes with European physical-second labels. No European source values are transformed or scored.
\newpage
"""
)
p2 = r"""{\Large\bfseries Complete airport accounts and denominators\par}
The rate denominator contains eligible completed nondiverted source records. Negative early arrivals remain eligible. The early-arrival-clamped field was not substituted. Missing or malformed values remain explicit.

{\small\setlength{\tabcolsep}{7pt}
\begin{tabular}{@{}lrr@{}}\toprule
Source account & ORD & ATL\\\midrule
"""
for label, field in [
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
]:
    p2 += (
        label
        + " & "
        + airport("ORD", field)
        + " & "
        + airport("ATL", field)
        + r" \\"
        + "\n"
    )
p2 += r"""\bottomrule\end{tabular}}

\heading{All fixed recorded-minute thresholds}
{\small\setlength{\tabcolsep}{7pt}
\begin{tabular}{@{}llrr@{}}\toprule
Cutoff & Quantity & ORD & ATL\\\midrule
"""
for cutoff in [14, 15, 16]:
    p2 += (
        "Recorded delay >= "
        + str(cutoff)
        + " & Positive count & "
        + airport("ORD", "count_ge" + str(cutoff))
        + " & "
        + airport("ATL", "count_ge" + str(cutoff))
        + r" \\"
        + "\n"
    )
    p2 += (
        " & Percent of eligible & "
        + airport("ORD", "rate_ge" + str(cutoff), "percent2")
        + r"\% & "
        + airport("ATL", "rate_ge" + str(cutoff), "percent2")
        + r"\% \\"
        + "\n"
    )
p2 += (
    r"""\bottomrule\end{tabular}}

Fifteen follows the source indicator definition; 14 and 16 are prespecified one-minute probes, not optimized replacements. The primary rate difference is the exact recorded bin $15 \leq \text{ArrDelay}<16$ divided by the eligible count. As a share of the recorded >=15 positives, that bin is """
    + airport("ORD", "boundary_fraction_of_ge15", "percent2")
    + r"""\% at ORD and """
    + airport("ATL", "boundary_fraction_of_ge15", "percent2")
    + r"""\% at ATL. A zero denominator is unavailable, never silently zero.

\heading{Complete case retention}
The repository exports all """
    + headline("airport_days")
    + r""" airport-day accounts, """
    + headline("airport_carrier_cases")
    + r""" airport/carrier accounts and """
    + headline("threshold_cases")
    + r""" threshold cases. Every day is retained. The carrier grid includes zero-row combinations with unavailable rates and all source code labels; it does not rank carrier quality. Agreement with the source indicator in this finite cohort does not establish general source accuracy, physical seconds or cross-system equivalence.
\newpage
"""
)
p3 = (
    r"""{\Large\bfseries Verification, implementation and next evidence\par}

\heading{Independent evidence}
A separate pandas C parser, SQLite key classification and exact Fraction values reconcile the captured native source in """
    + checked("native_source_conditions")
    + r""" finite conditions. Saved native-bound source checks pass """
    + checked("saved_source_conditions")
    + r""". An independent weighted SQLite/Fraction checker reconstructs all accounts, thresholds, numerators, denominators and example requests in """
    + checked("independent_analysis_conditions")
    + r""" conditions without importing the production metric functions.

The committed freeze binds """
    + checked("actual_frozen_dependencies")
    + r""" actual source/method dependencies before threshold comparisons. Source values were visible during capture and reconciliation; this was source informed, not blinded. The """
    + checked("authored_fixture_methods")
    + r""" authored fixture methods cover exact cutoff and fractional-minute values, negative delay, unknown fields, operation flags, duplicate groups, zero denominators, indicator disagreement and unsupported interpretations.

Separate full-history CPython """
    + bind("results/reproduction_cpython310.json", ["python"])
    + r""" and """
    + bind("results/reproduction_cpython312.json", ["python"])
    + r""" replays reproduce """
    + bind(
        "results/reproduction_cpython310.json", ["reproduced_files"], operation="length"
    )
    + r""" result files exactly, preserving """
    + bind("results/reproduction_cpython310.json", ["unchanged_source_files"])
    + r""" source-directory files in each. Figure checks bind """
    + bind("figures/verification.json", ["source_bound_artists"])
    + r""" bars and """
    + bind("figures/verification.json", ["svg_coordinate_conditions"])
    + r""" actual SVG coordinate conditions. These finite checks are not universal correctness guarantees.

\heading{Runnable implementation exercise}
Seven complete requests accept two qualified recorded-minute rate descriptions and reject five unsupported requests. The interface retains the actual numerator, eligible denominator and exact ratio, plus explicit unknown physical-second and European equivalence. It checks supplied verified accounts; it does not certify arbitrary caller input.

\begin{verbatim}
python -m pip install -r requirements.txt
python src/replay.py --out ../arrival-label-replay
\end{verbatim}
Use a new output directory. The replay checks frozen saved source counts; it does not reacquire the archive or establish original publication timing.

\heading{Material limits}
One winter month, two destination codes and one reporting-carrier source form a convenience cohort. Current historical data can be revised, and the dataset is not an immutable original-vintage capture. Recorded-minute values do not recover the physical-second distribution. No cross-region calibration, causal airport effect, carrier safety/quality score, new estimator, production deployment or realized saving is claimed.

A transfer follow-up needs threshold-resolved compatible targets, aligned operated/cancelled populations, suitable source rights and verified dated availability. Formal-publication projects, including Azure optimization, remain private. Public artifacts contain minimal federal statistical counts and original analysis; native flight identities, tail numbers and source files remain private.

{\small Source: U.S. Department of Transportation, Bureau of Transportation Statistics.
\url{https://transtats.bts.gov/PREZIP/}.
Official field definitions, exact indexed archive URL, capture/member hashes and failed-form history are retained in the repository. This independent study is not endorsed by DOT/BTS. MIT covers original code; source facts are attributed separately.}
"""
)
figs = []
for title, name in [
    ("Recorded threshold rates", "threshold_rates"),
    ("Every fixed source day", "daily_boundary"),
    ("Source eligibility and indicator reconciliation", "source_denominators"),
]:
    figs.append(
        r"\begin{landscape}"
        + "\n"
        + r"{\large\bfseries "
        + title
        + r"\par}"
        + "\n"
        + r"\begin{center}\includegraphics[width=9.4in,height=6.25in,keepaspectratio]{images/"
        + name
        + r".pdf}\end{center}"
        + "\n"
        + r"\end{landscape}"
        + "\n"
    )
tex = p1 + p2 + p3 + "".join(figs) + r"\end{document}" + "\n"
definitions = "\n".join(
    "\\newcommand{\\" + r["name"] + "}{" + r["display"] + "}" for r in bindings
)
tex = tex.replace("%%BINDINGS%%", definitions)
paper = ROOT / "paper"
(paper / "images").mkdir(exist_ok=True)
for name in ["threshold_rates", "daily_boundary", "source_denominators"]:
    shutil.copy2(ROOT / "figures" / (name + ".pdf"), paper / "images" / (name + ".pdf"))
(paper / "main.tex").write_bytes(tex.rstrip().encode() + b"\n")
(paper / "bindings.json").write_bytes((json.dumps(bindings, indent=2) + "\n").encode())
print("SOURCE_BOUND_MANUSCRIPT_WRITTEN", len(bindings))
