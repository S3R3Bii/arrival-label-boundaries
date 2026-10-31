# Keep a delay label attached to its denominator

Run the saved-data replay described in the README, then inspect results/exercise.json. The seven requests were fixed before comparison.

Two requests return a qualified recorded-minute numerator, eligible denominator and exact rate: ORD at >=15 minutes and ATL at >=16. Five requests reject European OTP15, physical-second lateness, a safety ranking, a transfer score and a missing airport.

Read src/exercise.py and tests/test_boundaries.py. Explain why 15.5 is inside the primary boundary bin, why negative early arrivals remain eligible, why whole duplicate-key groups are quarantined, and why an empty denominator is unavailable rather than zero. Keep cancelled and diverted counts visible beside the eligible rate.

For an implementation extension, add a caller-facing label contract that carries field name, cutoff, population, source vintage and unknown physical-second equivalence. Preserve the frozen research files; add a separate module and relevant boundary tests. Do not interpret a source-count result as a certified arbitrary input, safety score or European rate.
