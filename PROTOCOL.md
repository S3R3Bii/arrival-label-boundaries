# Fixed recorded-minute arrival-label audit

## Decision and original hold

Quantify how many recorded flights change arrival-delay labels when a minute-valued cutoff changes, before transferring a benchmark's target definition. The decision is whether an analyst has preserved a label and denominator contract, not whether one airport or carrier is better.

Original Study 09 asks whether a US-trained delay model transfers to European aggregates. Its common-event, population, source-rights and vintage gates remain unresolved. BTS's published delay event and EUROCONTROL OTP15 are not directly interchangeable. No European source values will be copied, transformed or scored. No transfer model, calibration, European performance rate or universal threshold conversion is claimed.

This separate source-informed measurement audit uses one US reporting-carrier source, a fixed month and two fixed destination codes. Metadata and official field definitions have been inspected; no flight records or source outcomes have been retrieved. Source values will be visible during ingestion and reconciliation. Committed chronology is not blindness.

## Fixed source capture

Use the official BTS TranStats Reporting Carrier On-Time Performance (1987-present) full prezipped file for January 2024, selected through its documented download form. Do not substitute the marketing-carrier dataset, another month, another mirror or a different airport pair after outcomes. Capture the exact resulting official archive URL, HTTP/browser retrieval evidence, native ZIP bytes and SHA256, member names/size/hashes and CSV headers. Metadata pages and source hash receipts remain available. Native archive/full CSV remain private.

Select every native row whose destination code is exactly ORD or ATL and source flight date is in January 2024. Preserve all national rows for capture count controls and all selected rows for exclusion accounting. Require a nonempty fixed airport cohort and all required columns. A wrong dataset/month, unreadable archive, unexpected structural schema, conflicting month assertions or missing selected airport fails the source gate. A demonstrated request/implementation error permits one targeted repair; no unchanged denial retry, user-agent rotation or access-control workaround.

Required fields: Year, Month, FlightDate, Reporting_Airline, DOT_ID_Reporting_Airline, Flight_Number_Reporting_Airline, Origin, OriginAirportID, Dest, DestAirportID, CRSDepTime, ArrDelay, ArrDel15, Cancelled and Diverted. Parse source flight dates strictly as documented compact YYYYMMDD or exact ISO YYYY-MM-DD if emitted by this archive; retain original format evidence. Year/month assertions must agree. Do not interpret local clock fields as UTC.

Within this one-month source, identify rows by source flight date, DOT reporting-carrier ID, reporting flight number, origin airport ID, destination airport ID and CRS departure-time token. Do not claim that this is a globally immutable flight identifier. Retain missing keys and whole duplicate-key groups; do not silently deduplicate or choose a preferred record. Tail numbers, route-level flight identities and native source narratives stay private. Public source sufficient cells are grouped by day, destination, carrier ID/code, eligibility category, recorded delay token and official indicator state, with counts only.

## Eligibility and explicit denominators

Retain all selected source records for total accounting. In precedence order, classify missing key, duplicate key, unknown cancellation/diversion flags, both flags set, cancelled, diverted, unknown/nonfinite delay, then eligible completed nondiverted record. Accept operation flags only when numeric source value is exactly 0 or 1. Do not silently map missing or malformed flags to zero. Both flags set remains a separate source inconsistency.

Parse recorded ArrDelay as an exact finite decimal, retaining negative early arrivals and any fractional values actually supplied. Missing, nonnumeric and nonfinite values remain unknown. Do not substitute the early-arrival-clamped ArrDelayMinutes field. The primary rate denominator is eligible source records only. Scheduled-source denominators, cancellations, diversions and all eligibility exclusions are exported separately, never merged into a completed-flight rate.

Retain ArrDel15 independently as 0, 1, missing or invalid. For eligible records with a usable official indicator, compare that source indicator with the rule recorded ArrDelay >= 15. Report every mismatch and missing/invalid indicator count. A mismatch is a source reconciliation observation, not proof of agency error. Keep source flags and reconstructed labels distinct.

## Fixed comparisons

Compute every eligible threshold count/rate for recorded delay >= 14, >= 15 and >= 16 minutes. Fifteen comes from the official source indicator definition; 14 and 16 are fixed one-minute sensitivity probes, not optimized definitions or claims about actual seconds. No threshold is selected after outcomes.

Primary sensitivity is (count_ge15 - count_ge16) / eligible_count, exactly the fraction of eligible records with 15 <= recorded delay < 16. Also retain that bin as a fraction of count_ge15, unavailable when the denominator is zero. Export the [14,15) and [15,16) bins, all three complete threshold numerators, exact ratios and official-indicator reconciliation. Missing denominators remain unavailable, not zero.

Report full-month airport accounts, every one of 31 airport-day accounts for both fixed airports, and complete airport/carrier accounts for every reporting-carrier ID observed in either selected cohort. Include zero-row airport/carrier cells with explicit unavailable rates; do not impose an outcome-dependent minimum-size filter or rank carrier quality. Treat carrier code changes within ID as source labels, retaining all codes.

Three planned figures: airport threshold rates with units and denominators; all 62 daily primary-sensitivity values with unknown states; and complete source eligibility/indicator reconciliation counts. Preserve both airports and every fixed day. Zero baselines and source-bound actual-geometry checks are required. No unobserved physical-second distribution, European target or cross-region effect may be inferred from recorded minutes.

## Freeze, independent checks and implementation

Implement capture/ingestion and independently verify native record counts, selected rows, key multiplicities, exact source delay tokens, flags, grouping and projection hashes. Use an independent second CSV parser plus SQLite/exact rational controls; do not rely only on the projection's own receipt. Commit the source projection, method code, environment, meaningful authored fixtures and actual dependency hashes before threshold comparisons. Source values remain source informed, not blinded.

Meaningful boundaries include negative delay, exactly 14/15/16 minutes, fractional 15.5, missing/nonfinite delay, zero denominators, official-indicator mismatch, unknown flags, both flags set, cancelled/diverted separation, whole duplicate groups and ambiguous local-clock/seconds assumptions. A runnable exercise must return qualified source-bound threshold counts and reject requests to equate a recorded-minute rate with European OTP15, infer seconds, rank safety or claim a transfer score.

Before release, independently reconstruct every saved cell/account/ratio, official-indicator discrepancy, daily/carrier case and exercise request. Run two isolated full-history saved-data replays with recorded Python versions. Check actual figure coordinates and source values, used manuscript bindings and every rendered page, bounded staged/canonical publication bytes and explicit independent-manuscript scope. Require exact candidate/main Linux success, identical tested/merged trees, verified annotated tag and accurate portfolio metadata.

## Acceptance and claim limits

Source rights/scope, complete source accounting, independent exact arithmetic, meaningful boundaries, readable full-case figures and prose, privacy and exact remote release evidence are pass/fail gates. Unknown or failed gates are not completion. Preserve failed receipts and the original transfer-study hold.

One winter month and two destination codes in one reporting-carrier source are a finite convenience cohort. Results are descriptive recorded-label sensitivity, not true physical-second lateness, national reliability, carrier quality, airport causality, model calibration, a new estimator, operational deployment or measured savings. A cross-region follow-up requires threshold-resolved compatible values, aligned populations, suitable rights and verified dated availability. Separate formal-publication projects including Azure optimization remain private.
