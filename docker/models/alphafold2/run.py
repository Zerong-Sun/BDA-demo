#!/usr/bin/env python3
import json
import os
from pathlib import Path

out = Path(os.environ.get("BDA_OUTPUT_DIR", "/output"))
out.mkdir(parents=True, exist_ok=True)
pdb = out / "predicted.pdb"
pdb.write_text("REMARK BDA stub AlphaFold2 output\nEND\n")
print(json.dumps({"structure": str(pdb), "plddt": 85.2}))
