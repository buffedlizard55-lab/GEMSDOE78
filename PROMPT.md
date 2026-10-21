# GEMSDOE78 Project Prompt - Master Document

**Last Updated:** 2026-10-21  
**Status:** ACTIVE - Generating Unique TIF Submissions for DOE GEMS Competition  
**Current Leaderboard High:** 0.4413 (from [DrivenData Leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/))  
**Our Best Holdout-DTI:** 0.1826 (H78-A strike-steered, 44,090 dots)  
**Target:** Generate submissions scoring > 0.3195, ultimately > 0.4413

---

## 🎯 MISSION STATEMENT

**MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION.** 
DO NOT COPY A PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION. 
WE MUST GENERATE A UNIQUE TIF SUBMISSION. 
IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION.

**There should be an easy to download submission TIF file as described by the prompt.** 
A lot of sites mention inspection only and a human inspector, but the inspection needs to be done through the project and needs to be validated for submission without human intervention.

---

## 🏆 COMPETITION DETAILS

- **Competition:** DOE GEMS (Geothermal Energy from Mineral Systems) - DrivenData Competition #306
- **Goal:** Predict locations of undiscovered faults in the Great Basin, Nevada
- **Metric:** DTI (Detection Tversky Index) with α=0.2, β=0.8, 300m triangular kernel
- **Submission Format:** Single-band GeoTIFF, EPSG:32611, 3730×3292 pixels, 100m resolution
- **Value Range:** [0, 1] (binary recommended - each pixel 0 or 1)
- **Constraints:** Predicted values MUST be in range [0, 1]
- **Footprint:** 5,167,373 pixels (catalogue has 60,988 pixels in 3,199 components)

**Official Resources:**
- [Competition Page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [Reference Solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [GeoDAWN Data](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [INGENIOUS Project](https://gbcge.org/current-projects/ingenious/)
- [EPSG:32611](https://epsg.io/32611)
- [Tversky Index](https://en.wikipedia.org/wiki/Tversky_index)

---

## 📊 CURRENT SCORE ANALYSIS

### Family Scores (Owner-Reported)

| Repository | Submission | Score | Notes |
|------------|------------|-------|-------|
| GEMSDOE32 | h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros | **0.2778** | Family's best - emission optimization |
| GEMSDOE | gems-submission-20260925T001403Z-7f00890a | 0.1563 | Baseline |
| GEMSDOE2 | gemsdoe2-dual-family-union | 0.1560 | Union approach |
| GEMSDOE24 | h25-1-dotted-h19-5-d1-5 | 0.2477 | Dotted emission |
| GEMSDOE25 | dotted-h19-5-d2-8 | 0.2600 | Optimal spacing |
| GEMSDOE27 | topo-gap-closure-t-v2-on-d1-5 | 0.2449 | Gap closure |
| GEMSDOE28 | h36-1-rung30-blind-r1 | 0.2710 | Blind approach |
| GEMSDOE28 | h32-1-prethin-tip-euler-d2-8 | 0.2649 | Tip detection |
| GEMSDOE30 | d28-poisson300m-offcat-44090 | 0.2600 | Poisson sampling |
| GEMSDOE31 | h27-4-solo-d28 | 0.2708 | Solo emission |
| GEMSDOE32 | anderson-geothermal-pinn-38854 | 0.2750 | Confirmation of H33 basin |
| GEMSDOE33 | h33d-analog-tip-stepover-r30 | 0.2632 | Tip/step-over |
| GEMSDOE36 | anderson-geothermal-pinn-38854 | 0.2750 | Pinnacle approach |
| **GEMSDOE78** | **gems78-h78a-strike-steered-44090dots** | **0.1826 (HOLDOUT-DTI)** | **Our current best** |

### Public Leaderboard (2026-10-21)
- **#1:** 0.4413 (xiaofanhu)
- **#2:** 0.3904 (cfld__)
- **Target:** Beat 0.3195 → 0.4413

---

## 🔬 WHY H33 SCORED 0.2778

From `docs/why-h33.md` and `research/h78_hypotheses.md`:

### The Scoring Law
DTI(α=0.2, β=0.8, R=300m triangular) = TPw / (TPw + 0.2·FPw + 0.8·FNw)

**Key Insight:** A dot helps only when its max-credit exceeds ≈ 0.2 × DTI
- At DTI=0.16: break-even = 0.032
- At DTI=0.28: break-even = 0.056

### H33's Chain of Gains
1. **H19-5 solid:** 121,131 line pixels → 0.1922
2. **D2.8 dots:** 44,090 binary dots (spacing ≥ 2.83px) → 0.2600 (+0.0678)
3. **H33-2-B2:** Removed 6,436 dots within 2px of catalogue → 0.2778 (+0.0178)

**All gains are emission-side on one unchanged detector field!**

### Why It Worked
- **Emission Geometry:** Sparse dots at optimal spacing (2.83px = 283m) match the 300m kernel
- **Flank Pruning:** Removing dots ≤2px from catalogue eliminates zero-credit mass
- **Credit Density:** Each dot earns mean credit ~0.13; need ~0.16 per dot to reach 0.32

### What It Cannot Do
- Cannot thin further for free (near break-even at 0.056)
- To beat 0.2778, need better **ranking** of candidate pixels (detector problem)
- Hidden faults are >200m from catalogue (median 19.6px = ~2km)

---

## 🎯 PARALLEL-RUN PROTOCOL

**READ FIRST - This session is one of several running from this same prompt.**

### 1. LANE DISCIPLINE
Your lane is the single method paragraph below. Stay inside it.

**Drift Detection:** If your raster's rank-correlation with any registry raster exceeds [0.90], 
or more than [70%] of your dots fall within 3px of one registry raster's dots, you have drifted 
into another lane: **LOG IT AS A DUPLICATE AND STOP.**

**Check this on the surface before placement AND on the final dots.**

### 2. REUSE, DON'T REBUILD
- Use the template's cached feature stack
- Use `evaluate_holdout.py` and `submission_writer.py`
- **Holdout = hide-and-recover:** 
  - Withhold whole fault segments with a buffer
  - Derive every catalogue-based feature ONLY from visible faults
  - Mask visible faults pixel-exactly
  - Score pooled DTI (α=0.2, β=0.8, 300m triangular kernel)
- If a shared tool is wrong, fix it once in the template and report it
- **NEVER keep a private fork**

### 3. LABEL EVERY NUMBER
- **HOLDOUT-DTI:** (evaluator version, number of withheld positives, 95% CI)
- **ORGANIZER-CONFIRMED:** (copied from a submission-page receipt)
- **A projection is NEVER written as a score**

### 4. LEAKAGE CANARY
Test each feature alone on the holdout before trusting any result.
**AUC above [0.90] means leakage until proven otherwise.**

### 5. RUN CARD
End with one JSON card containing:
- hypothesis
- mechanism
- the named non-fault process that could mimic it
- holdout DTI + CI
- correlation/overlap vs registry
- raster sha256
- validator output (no NaN inside footprint, values in [0,1], CRS/shape/transform match)
- submission name + note of at most 140 characters
- verdict: promote / negative

**Negative results are deliverables.**

### 6. BUDGET
Stop after [3] experiments or [2] hours.
Do not pick submissions: promotion to a real slot is a separate selector step, 
within the weekly cap shown on the submission page.

---

## 🚀 STRATEGY TO BEAT 0.3195 → 0.4413

### Current Understanding
1. **Emission optimization is maxed out** (H33 at 0.2778)
2. **Detector improvement is the path forward**
3. **Holdout-DTI ≠ Live Score** (H33: holdout unknown, live=0.2778)
4. **Need better ranking of candidate pixels**

### What We Know Works
- Multi-physics lineament corroboration (H19-5: 0.1922)
- Dotted emission at 2.83px spacing (D2.8: 0.2600)
- Catalogue flank pruning at 2px (H33: 0.2778)
- Strike-steered features (H78-A: 0.1826 holdout-DTI)

### What We Need to Try
**NEW DETECTOR APPROACHES that haven't been implemented:**

---

## 📋 REQUIRED DELIVERABLES

### For This Session
1. ✅ Review the repo (DONE)
2. 🔄 Generate 3-5 NEW candidate geological hypotheses
3. 🔄 Rank by expected DTI improvement and implementation cost
4. 🔄 Validate top candidate on spatially-blocked holdout set
5. 🔄 Generate UNIQUE TIF submission
6. 🔄 Create executive summary with downloadable TIF
7. 🔄 Verify TIF passes all validation checks

### File Structure
```
GEMSDOE78/
├── PROMPT.md                    # This file - read every session
├── README.md                    # Project status and how to submit
├── docs/
│   ├── index.html               # GitHub Pages site
│   ├── executive-summary.html   # How to submit, download links
│   ├── h78mpc.html              # Alternative candidate page
│   └── downloads/
│       ├── submission.tif       # Primary TIF file
│       ├── submission.zip       # Zipped version
│       └── submission.json      # Run card metadata
├── evidence/
│   ├── h78_run_card.json        # Full run card
│   └── ...json                  # All experiment evidence
├── registry/
│   ├── preregistration.json     # Preregistered hypotheses
│   ├── data_manifest.json       # Data provenance
│   └── sources.json             # Verified sources
├── research/
│   ├── h78_hypotheses.md        # Hypothesis documentation
│   ├── knowledge.md             # Knowledge store
│   └── new_hypotheses.md        # NEW: This session's hypotheses
└── scripts/
    ├── build_submission.py      # Build TIF files
    ├── run_holdout.py            # Holdout evaluation
    └── verify_tif.py             # Validation
```

---

## 🔬 NEW HYPOTHESES TO GENERATE

**REQUIREMENT:** 3-5 candidate geological hypotheses we haven't tried yet, each naming:
1. The specific layer(s) involved
2. The physical signature being targeted
3. Why it should catch a fault missing from USGS/INGENIOUS catalogue
4. How it differs from anything already implemented
5. Expected DTI improvement
6. Implementation cost

**Rank by expected DTI improvement × cost.**

### Hypothesis Template
```markdown
#### H78-X: [Name]
- **Layers:** [list specific bands/features]
- **Physical Signature:** [edge-detection, curvature, etc.]
- **Target:** [what fault type it catches]
- **Why Missed by Catalogue:** [explanation]
- **Non-Fault Mimic:** [false positive risk]
- **Novelty:** [how different from existing]
- **Expected Gain:** [low/moderate/high]
- **Cost:** [low/medium/high]
- **Validation Status:** [not run / holdout tested / promoted]
```

---

## ⚡ CORE VALUES (Arena)

### 1. Maximize P(Win)
Every hour goes to the thing most likely to raise the organizer-confirmed score. 
A negative result that saves a submission slot counts.

### 2. Own the Outcome
- No manual steps
- No unlabelled numbers
- No hidden irregularities
- If a tool is wrong, fix it in the shared template and say so

---

## 📝 WORKFLOW FOR THIS SESSION

### Pass 1: Analysis & Hypothesis Generation
1. Review all existing submissions and scores
2. Analyze H33's success factors
3. Identify gaps in current approaches
4. Generate 3-5 new hypotheses
5. Rank by expected impact and feasibility

### Pass 2: Implementation
1. Implement top hypothesis
2. Run on holdout set
3. Validate uniqueness vs registry
4. Check leakage canaries
5. Generate TIF file

### Pass 3: Validation & Documentation
1. Run full validation suite
2. Create run card
3. Update documentation
4. Verify TIF is submission-ready

### Pass 4: Review & Merge
1. Review all changes
2. Verify no hallucinations
3. Create pull request
4. Merge to main

---

## 🎯 IMMEDIATE NEXT STEPS

1. **Read this PROMPT.md** at the start of every session
2. **Review README.md** for current status
3. **Check docs/why-h33.md** for H33 analysis
4. **Read research/h78_hypotheses.md** for existing hypotheses
5. **Generate NEW hypotheses** in research/new_hypotheses.md
6. **Implement and validate** the best candidate
7. **Generate submission TIF**
8. **Update GitHub Pages site**

---

## 🚨 CRITICAL CONSTRAINTS

1. **NO HALLUCINATIONS** - Every claim must be verifiable from official sources
2. **WORK LINE BY LINE** - Verify each statement
3. **NO MANUAL INPUT** - Work autonomously
4. **FLAG IRREGULARITIES** - For review
5. **ALL SOURCES MUST BE OFFICIAL AND VERIFIED**

---

## 📚 VERIFIED SOURCES

All sources in `registry/sources.json` with fetch status. 
Manual review links:
- [Competition Rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [DrivenData Competition Page](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Reference Solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [GeoDAWN Survey](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [INGENIOUS Project](https://gbcge.org/current-projects/ingenious/)
- [GDR 1391](https://gdr.openei.org/submissions/1391)

---

**REMEMBER: Read this file at the start of every session!**
