# Original project prompt (archived verbatim excerpt — read at the start of every session)

> Review the repo.
>
> THE FOLLOWING IS THE HIGHEST URGENCY AND MUST BE FOLLOWED!
>
> MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION. BUT WE MUST GENERATE A UNIQUE TIF SUBMISSION. IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION.
>
> There should be an easy to download submission tif file as described by the prompt. Read the entire prompt. A lot of sites mention inspection only and a human inspector, but the inspection needs to be done through the project and needs to be validated for submission without human intervention.
>
> PARALLEL-RUN PROTOCOL — read first. This session is one of several running from this same prompt.
>
> 1. LANE. Your lane is the single method paragraph below. Stay inside it. If your raster's rank-correlation with any registry raster exceeds [0.90], or more than [70%] of your dots fall within 3 px of one registry raster's dots, you have drifted into another lane: log it as a duplicate and stop. Check this on the surface before placement AND on the final dots.
> 2. REUSE, DON'T REBUILD. Use the template's cached feature stack, evaluate_holdout.py and submission_writer.py. Holdout = hide-and-recover: withhold whole fault segments with a buffer, derive every catalogue-based feature only from the visible faults, mask visible faults pixel-exactly, score pooled DTI (alpha 0.2, beta 0.8, 300 m triangular kernel). If a shared tool is wrong, fix it once in the template and report it; never keep a private fork.
> 3. LABEL EVERY NUMBER as HOLDOUT-DTI (evaluator version, number of withheld positives, 95% CI) or ORGANIZER-CONFIRMED (copied from a submission-page receipt). A projection is never written as a score.
> 4. LEAKAGE CANARY. Test each feature alone on the holdout before trusting any result. AUC above [0.90] means leakage until proven otherwise.
> 5. RUN CARD. End with one JSON card: hypothesis; mechanism; the named non-fault process that could mimic it; holdout DTI + CI; correlation/overlap vs registry; raster sha256; validator output (no NaN inside the footprint, values in [0,1], CRS/shape/transform match); submission name + note of at most 140 characters; verdict promote / negative. Negative results are deliverables.
> 6. BUDGET. Stop after [3] experiments or [2] hours. Do not pick submissions: promotion to a real slot is a separate selector step, within the weekly cap shown on the submission page.
>
> WE NEED TO STUDY, ANALYZE, AND UNDERSTAND THE HIGHEST SCORE FROM THE GEMDOE SITE WHERE THE SUBMISSION TIF IS DOWNLOADED FROM WHICH IS THE FOLLOWING: https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html — h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778. Why and how did this get the highest score and are we able to generate a submission that scores higher than 0.2778? Answer the question using PhD level experience, knowledge, and judgement. Then use the answer to generate a unique TIF submission into the competition. Must be unique submission unlike any within the GEMSDOE sites above. Verify working line by line no hallucinations. Current competition leaderboard GEMSDOE high score: 0.4413. [0.3195 is the highest score right now so we need to design a new strategy …]
>
> Before implementing, generate 3–5 candidate geological hypotheses we haven't tried yet, each naming: the specific layer(s) involved, the physical signature being targeted, why it should catch a fault missing from the USGS/INGENIOUS catalogue rather than one already in it, and how it differs from anything already implemented in this repo. Rank them by expected DTI improvement and implementation cost. Validate the top candidate on our spatially-blocked holdout set before touching a weekly submission slot — do not spend a submission slot on an idea that hasn't beaten the current holdout best. If a candidate can't be validated without new external data, name the specific free, official source needed and check it's obtainable before proposing the idea as viable.
>
> Work line by line verifying from official verified trusted sources, provide links for manual review. There should be no manual input, work on your own to complete tasks. Flag any irregularities for review. No hallucinations.
>
> Put this prompt into the repo readme and read it every time we work on the project as a starting point … It should solve the problem of having to manually check everything ourselves and having an up to date current feed.
>
> Core Values (Arena): Maximize P(Win); Own the Outcome.
>
> The site should be able to generate a TIF file that is required for submission. It should be as easy as download to click a File to submit into the competition. This needs to be in the executive summary or the very beginning of the site. It should be obvious when you visit the site. [Earlier portal error on a downloaded file: "Predicted values must be in range [0, 1]".] Also we need to give it a unique name and a short comment … Create an executive summary subpage that explains exactly how to make a submission into the contest.
>
> Competition: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ · rules https://www.drivendata.org/competitions/306/competition-doe-gems/ · about page/968 · data tab (login) · reference solution https://github.com/drivendataorg/gems-prize-reference-solution · rules PDF https://docs.nlr.gov/docs/fy26osti/96647.pdf · GDR 1391 https://gdr.openei.org/submissions/1391 · GeoDAWN https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and · INGENIOUS https://gbcge.org/current-projects/ingenious/ · EPSG:32611 https://epsg.io/32611 · Tversky https://en.wikipedia.org/wiki/Tversky_index · leaderboard https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/
>
> Run this task through multiple passes (implement+verify; review for bugs/missing requirements; re-check against the original request). Create a pull request and merge it onto main. Make suggestions for what work still needs to be done and any limitations.

The full list of sibling sites and their owner-reported scores supplied with the prompt is preserved in
`registry/family_scores.csv` (copied from GEMSDOE77 `registry/live_scores.csv`, which transcribed the same list).
