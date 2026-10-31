# Saved count-cell meanings

Every selected native row contributes to one source cell. Cells retain the source day, fixed destination, reporting-carrier ID/code, explicit eligibility category, operation flags, exact recorded delay value and official indicator state, with a positive record count. The public file omits tail numbers and flight-level identities. Native ZIP/member hashes and independent parser controls bind these counts to the captured source.

The delay field is ArrDelay, which retains negative early arrivals. ArrDelayMinutes was not substituted. Numeric parsing preserves finite decimal values; missing, invalid and nonfinite tokens remain unknown. Completed nondiverted eligible records form the rate denominator. Cancellations, diversions, ambiguous keys and unavailable fields remain in total-source accounting. Both operation flags set is a separate source inconsistency.

The source catalog retains all carrier-code labels and airport IDs observed in this one month. It does not establish globally permanent identity, carrier quality or historical first availability. A recorded value in the interval from 15 inclusive to 16 exclusive is a recorded-minute sensitivity bin. It does not identify a physical-second interval or a European OTP15 label.
