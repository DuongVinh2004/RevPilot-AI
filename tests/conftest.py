"""
RevPilot AI — Pytest Root Test Configuration & Fixtures
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND_SRC = ROOT / "packages" / "backend" / "src"

for p in (str(BACKEND_SRC), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

import os
os.environ.setdefault("WEBHOOK_SIGNING_SECRET", "whsec_default_secret_2026")
