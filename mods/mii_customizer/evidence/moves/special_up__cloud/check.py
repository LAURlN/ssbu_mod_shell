#!/usr/bin/env python3
"""Offline check of MV-special_up__cloud (run from the workspace root; exit 1 on mismatch).

The checks are shared with MV-aerial_forward__cloud (same sword, banks and checker):
evidence/moves/aerial_forward__cloud/check.py. This runs them for this unit plus the shared sword assets.

    python -I mods/mii_customizer/evidence/moves/special_up__cloud/check.py
"""
import runpy
import sys
from pathlib import Path

shared = Path(__file__).resolve().parents[1] / 'aerial_forward__cloud' / 'check.py'
sys.argv = [str(shared), '--unit', 'special_up__cloud'] + sys.argv[1:]
runpy.run_path(str(shared), run_name='__main__')
