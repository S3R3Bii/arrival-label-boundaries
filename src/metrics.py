"""Exact weighted source-record accounts; recorded minutes are not physical seconds."""

from collections import Counter
from fractions import Fraction

CATEGORIES = [
    "MISSING_KEY",
    "DUPLICATE_KEY",
    "UNKNOWN_OPERATION_FLAGS",
    "BOTH_OPERATION_FLAGS",
    "CANCELLED",
    "DIVERTED",
    "UNKNOWN_DELAY",
    "ELIGIBLE",
]


def account(cells):
    counts = Counter()
    ge = {k: 0 for k in [14, 15, 16]}
    official_known = official_positive = mismatch = 0
    raw_cancelled = raw_diverted = 0
    for row in cells:
        n = int(row["records"])
        assert n > 0 and row["category"] in CATEGORIES
        counts[row["category"]] += n
        raw_cancelled += n * (row["cancelled_flag"] == "1")
        raw_diverted += n * (row["diverted_flag"] == "1")
        if row["category"] != "ELIGIBLE":
            continue
        assert (
            row["delay_state"] == "FINITE"
            and row["cancelled_flag"] == row["diverted_flag"] == "0"
        )
        value = Fraction(row["delay_token"])
        for cutoff in ge:
            ge[cutoff] += n * (value >= cutoff)
        if row["official_indicator"] in ["0", "1"]:
            official_known += n
            official_positive += n * (row["official_indicator"] == "1")
            mismatch += n * (int(row["official_indicator"]) != int(value >= 15))
    eligible = counts["ELIGIBLE"]
    boundary = ge[15] - ge[16]
    result = dict(
        source_records=sum(counts.values()),
        eligible_records=eligible,
        missing_key_records=counts["MISSING_KEY"],
        duplicate_key_records=counts["DUPLICATE_KEY"],
        unknown_operation_flag_records=counts["UNKNOWN_OPERATION_FLAGS"],
        both_operation_flags_records=counts["BOTH_OPERATION_FLAGS"],
        cancelled_records=counts["CANCELLED"],
        diverted_records=counts["DIVERTED"],
        unknown_delay_records=counts["UNKNOWN_DELAY"],
        raw_cancelled_flag_records=raw_cancelled,
        raw_diverted_flag_records=raw_diverted,
        official_indicator_known=official_known,
        official_indicator_unknown=eligible - official_known,
        official_indicator_positive=official_positive,
        official_indicator_mismatch=mismatch,
        count_ge14=ge[14],
        count_ge15=ge[15],
        count_ge16=ge[16],
        rate_ge14=str(Fraction(ge[14], eligible)) if eligible else "",
        rate_ge15=str(Fraction(ge[15], eligible)) if eligible else "",
        rate_ge16=str(Fraction(ge[16], eligible)) if eligible else "",
        count_14_to_15=ge[14] - ge[15],
        count_15_to_16=boundary,
        boundary_fraction=str(Fraction(boundary, eligible)) if eligible else "",
        boundary_fraction_of_ge15=str(Fraction(boundary, ge[15])) if ge[15] else "",
    )
    return result
