"""Single source of truth for the fixed evaluation-row construction shared by
local_shap_pipeline.py, deletion_curve.py, and insertion_curve.py.

Before this module existed, N_EVAL_ROWS=20 and EVAL_SEED=12345 were defined
independently in all three scripts (deletion_curve.py and insertion_curve.py
had 20 as a bare literal, not even a named constant). They agreed only
because the duplicated values happened to match -- nothing enforced it, so a
future edit to one copy would have silently detached that script's eval set
from the other two. See docs/measurement_protocol.md Sec 2.1 for what these
values mean; do not change them here without re-deriving every downstream
result that depends on the current 14-row eval set.
"""
N_EVAL_ROWS = 20
EVAL_SEED = 12345  # fixed across ALL configs -- same rows for every comparison
