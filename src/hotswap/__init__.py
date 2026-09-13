"""Hot-swap retraining audit log.

Step 1 of hot-swap retraining: the append-only event log only. No
retraining logic, no model swap, no UI lives here -- see audit_log.py's
module docstring for the reproducibility contract this package exists to
enforce.
"""
