#!/usr/bin/env python3
import json
import os
from pathlib import Path

out = Path(os.environ.get("BDA_OUTPUT_DIR", "/output"))
out.mkdir(parents=True, exist_ok=True)
pdb = out / "relaxed.pdb"
pdb.write_text("REMARK BDA stub Rosetta output\nEND\n")
print(json.dumps({"relaxed_pdb": str(pdb), "interface_score": -12.5}))
