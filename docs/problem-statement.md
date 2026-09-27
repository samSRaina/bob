# Problem Statement

**IBM Bob AI Hackathon x NFSU - Problem Statement #10 (Track 4: AI & Predictive)**
**"FIR Intelligence & Crime Pattern Detector"**

## Background

Uttar Pradesh Police's CCTNS (Crime and Criminal Tracking Network & Systems) holds
over 3 crore digitized First Information Reports (FIRs). Every FIR is typed or
scanned into a standard e-format - district, station, sections of law, complainant,
accused, modus operandi - but the system has no NLP layer. Each FIR exists as an
isolated document. Nothing in CCTNS today reads two FIRs together and asks: *are
these the same person, or the same crew, operating under different names in
different districts?*

## The Problem

Serial and inter-district offenders evade detection specifically because FIR-to-FIR
connections are never surfaced. The real case anchoring this problem statement is
the Jamtara (Jharkhand) SIM-swap/UPI-fraud ring: cells of the same operation filed
FIRs across multiple states and districts for years before investigators manually
pieced together that they were connected - by which point over 95,000 UPI fraud
cases (FY2023 alone) had accumulated. The connecting evidence was almost always
sitting in the records the whole time: a reused phone number, a reused vehicle, a
name spelled three different ways, or a fraud script repeated nearly word-for-word
two districts over. No investigator has the time to manually cross-reference every
new FIR against three crore existing ones by hand.

## Who is Affected

- **Station House Officers (SHOs)** and **Station Officers (PI-level)**, who file
  and investigate FIRs at the police-station level and have no way to know if
  "their" FIR is part of a larger pattern outside their jurisdiction.
- **District Superintendents of Police (SPs)**, who need a station-trend view
  across their district but currently rely on informal coordination between
  station houses.
- **State-level crime analysts / DGP office**, who need to spot cross-district
  syndicates early - before the pattern is obvious only in hindsight, after dozens
  of victims.

## Why It Matters

- 80,000+ children reported missing annually in India (NCRB 2022) - the same
  identity-linking problem applies whenever a case reappears under a name variant
  or partial description.
- The Jamtara-style fraud pattern scales linearly with detection delay: every week
  a cross-district link goes unnoticed is another week the same script runs on new
  victims in a new district.
- Investigators currently do this cross-referencing manually, if at all - it does
  not scale past a handful of FIRs an officer personally remembers.

## Why Existing Solutions Fall Short

CCTNS stores FIRs; it does not read them. There is no entity resolution across
name-transliteration variants (a single accused can appear as "Mohd. Aslam",
"Mohammad Aslaam", and "M. Aslam" across three FIRs with zero literal string
overlap), no modus-operandi similarity search, and no jurisdiction-aware access
control that would let a State DGP see cross-district patterns while a Station
Officer sees only their own beat. Generic keyword search over FIR text cannot
catch a paraphrased fraud script or a shared phone number across differently
worded reports - it requires the kind of semantic and identifier-level linking
this project builds.
