#!/usr/bin/env python3
import json
import os
import signal
import sys
from pathlib import Path


def _handle_sigterm(signum, frame):
    print(json.dumps({"status": "cancelled", "signal": signum}))
    sys.exit(143)


signal.signal(signal.SIGTERM, _handle_sigterm)
signal.signal(signal.SIGINT, _handle_sigterm)

out = Path(os.environ.get("BDA_OUTPUT_DIR", "/output"))
out.mkdir(parents=True, exist_ok=True)
pdb = out / "predicted.pdb"
pdb.write_text("REMARK BDA stub AlphaFold2 output\nEND\n")
print(json.dumps({"structure": str(pdb), "plddt": 85.2}))
