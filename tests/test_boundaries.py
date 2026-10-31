"""Authored source,threshold and denominator boundaries;not model-performance tests."""

from pathlib import Path
import sys, unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from metrics import account
from project_source import classify, day, numeric, flag
from exercise import describe


class RecordedBoundaryTests(unittest.TestCase):
    def cell(self, delay="15", n="1", **changes):
        out = dict(
            records=n,
            category="ELIGIBLE",
            delay_token=delay,
            delay_state="FINITE",
            cancelled_flag="0",
            diverted_flag="0",
            official_indicator="1",
        )
        out.update(changes)
        return out

    def test_exact_fixed_cutoffs(self):
        out = account([self.cell("14"), self.cell("15"), self.cell("16")])
        self.assertEqual([out["count_ge" + str(k)] for k in [14, 15, 16]], [3, 2, 1])

    def test_fractional_recorded_minutes_not_rounded(self):
        out = account([self.cell("15.5")])
        self.assertEqual(out["count_15_to_16"], 1)
        self.assertEqual(out["boundary_fraction"], "1")

    def test_negative_early_arrivals_retained_in_denominator(self):
        out = account([self.cell("-20", official_indicator="0"), self.cell("15")])
        self.assertEqual(out["eligible_records"], 2)
        self.assertEqual(out["rate_ge15"], "1/2")

    def test_weighted_sufficient_counts(self):
        out = account([self.cell("15", n="3"), self.cell("16", n="7")])
        self.assertEqual(out["source_records"], 10)
        self.assertEqual(out["boundary_fraction"], "3/10")

    def test_zero_denominator_unavailable(self):
        out = account([])
        self.assertEqual(out["source_records"], 0)
        self.assertEqual(out["rate_ge15"], "")
        self.assertEqual(out["boundary_fraction"], "")

    def test_no_positive_ge15_has_unavailable_conditional_bin(self):
        out = account([self.cell("10", official_indicator="0")])
        self.assertEqual(out["boundary_fraction"], "0")
        self.assertEqual(out["boundary_fraction_of_ge15"], "")

    def test_official_indicator_mismatch_retained(self):
        out = account(
            [
                self.cell("14", official_indicator="1"),
                self.cell("16", official_indicator="0"),
            ]
        )
        self.assertEqual(out["official_indicator_mismatch"], 2)
        self.assertEqual(out["eligible_records"], 2)

    def test_unknown_indicator_not_missing_delay(self):
        out = account([self.cell(official_indicator="MISSING")])
        self.assertEqual(out["eligible_records"], 1)
        self.assertEqual(out["official_indicator_unknown"], 1)

    def test_cancellation_diversion_and_completed_denominators_separate(self):
        out = account(
            [
                self.cell(category="CANCELLED", cancelled_flag="1"),
                self.cell(category="DIVERTED", diverted_flag="1"),
                self.cell("16"),
            ]
        )
        self.assertEqual(
            (
                out["source_records"],
                out["cancelled_records"],
                out["diverted_records"],
                out["eligible_records"],
            ),
            (3, 1, 1, 1),
        )

    def test_missing_delay_not_zero(self):
        out = account([self.cell("", category="UNKNOWN_DELAY", delay_state="MISSING")])
        self.assertEqual(out["unknown_delay_records"], 1)
        self.assertEqual(out["eligible_records"], 0)

    def test_nonpositive_cell_counts_rejected(self):
        with self.assertRaises(AssertionError):
            account([self.cell(n="0")])

    def test_contradictory_eligible_flags_rejected(self):
        with self.assertRaises(AssertionError):
            account([self.cell(cancelled_flag="1")])

    def test_whole_duplicate_key_category(self):
        self.assertEqual(classify(True, 2, "0", "0", "FINITE"), "DUPLICATE_KEY")
        self.assertEqual(classify(True, 9, "1", "0", "FINITE"), "DUPLICATE_KEY")

    def test_missing_key_precedes_other_eligibility(self):
        self.assertEqual(classify(False, 0, "1", "0", "MISSING"), "MISSING_KEY")

    def test_unknown_operation_flags_not_zero(self):
        self.assertEqual(
            classify(True, 1, "MISSING", "0", "FINITE"), "UNKNOWN_OPERATION_FLAGS"
        )

    def test_both_operation_flags_explicit(self):
        self.assertEqual(classify(True, 1, "1", "1", "FINITE"), "BOTH_OPERATION_FLAGS")

    def test_cancelled_and_diverted_precede_missing_arrival_delay(self):
        self.assertEqual(classify(True, 1, "1", "0", "MISSING"), "CANCELLED")
        self.assertEqual(classify(True, 1, "0", "1", "MISSING"), "DIVERTED")

    def test_flag_numeric_domain(self):
        self.assertEqual(flag("0.0"), "0")
        self.assertEqual(flag("1.0"), "1")
        self.assertEqual(flag("2"), "INVALID")
        self.assertEqual(flag("False"), "INVALID")

    def test_nonfinite_and_missing_delay_states(self):
        self.assertEqual(numeric("NaN"), ("", "NONFINITE"))
        self.assertEqual(numeric(""), ("", "MISSING"))
        self.assertEqual(numeric("bad"), ("", "INVALID"))

    def test_date_formats_and_invalid_leap_day(self):
        self.assertEqual(day("20240101"), "2024-01-01")
        self.assertEqual(day("2024-01-01"), "2024-01-01")
        self.assertIsNone(day("2023-02-29"))

    def test_local_clock_not_promoted_to_date_or_utc(self):
        self.assertIsNone(day("2359"))
        self.assertIsNone(day("2024-01-01T00:00:00Z"))


class InterfaceTests(unittest.TestCase):
    def request(self, **changes):
        out = dict(
            destination="ORD",
            measure="RECORDED_MINUTE_RATE",
            denominator="ELIGIBLE_COMPLETED_NONDIVERTED",
            cutoff=15,
        )
        out.update(changes)
        return out

    def accounts(self):
        return [
            dict(
                destination="ORD",
                eligible_records="10",
                count_ge15="2",
                rate_ge15="1/5",
            )
        ]

    def test_qualified_current_rate(self):
        out = describe(self.request(), self.accounts())
        self.assertTrue(out["accepted"])
        self.assertEqual(
            (out["numerator"], out["denominator"], out["rate_fraction"]), (2, 10, "1/5")
        )
        self.assertFalse(out["European_equivalence_known"])

    def test_physical_seconds_and_european_rate_rejected(self):
        for measure in ["PHYSICAL_SECOND_RATE", "EUROPEAN_OTP15"]:
            self.assertEqual(
                describe(self.request(measure=measure), self.accounts())["reason"],
                "UNSUPPORTED_MEASURE",
            )

    def test_safety_and_transfer_scores_rejected(self):
        for measure in ["CARRIER_SAFETY_RANK", "TRANSFER_SCORE"]:
            self.assertFalse(
                describe(self.request(measure=measure), self.accounts())["accepted"]
            )

    def test_denominator_change_rejected(self):
        self.assertEqual(
            describe(self.request(denominator="ALL_SCHEDULED"), self.accounts())[
                "reason"
            ],
            "DENOMINATOR_MISMATCH",
        )

    def test_unplanned_or_boolean_cutoff_rejected(self):
        for value in [True, 15.0, 17]:
            self.assertEqual(
                describe(self.request(cutoff=value), self.accounts())["reason"],
                "UNPLANNED_CUTOFF",
            )

    def test_unknown_or_duplicate_airport_rejected(self):
        self.assertEqual(
            describe(self.request(), [])["reason"], "AIRPORT_NOT_ESTABLISHED"
        )
        self.assertEqual(
            describe(self.request(), self.accounts() * 2)["reason"],
            "AIRPORT_NOT_ESTABLISHED",
        )

    def test_empty_eligible_denominator_rejected(self):
        self.assertEqual(
            describe(self.request(), [dict(destination="ORD", eligible_records="0")])[
                "reason"
            ],
            "NO_ELIGIBLE_DENOMINATOR",
        )

    def test_invalid_request_rejected(self):
        self.assertEqual(describe(None, [])["reason"], "INVALID_REQUEST")


if __name__ == "__main__":
    unittest.main()
