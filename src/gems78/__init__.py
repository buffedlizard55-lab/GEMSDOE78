"""GEMSDOE78 — lane H78: strike-steered lineament learning for DrivenData competition 306 (DOE GEMS).

Modules: data (input verification + 19-band stack), strike (regional catalogue-strike field),
features (isotropic + steered multi-scale derivatives), emit (flank prune, greedy ≥2.8 px dots),
pipeline (arms A0/A1/A2, HGB fits, scoring). Evaluation and writing reuse vendor/gems57 unchanged.
"""
__version__ = "0.1.0"
