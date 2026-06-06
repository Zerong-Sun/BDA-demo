#!/usr/bin/env python3
import json
import os
from pathlib import Path

out = Path(os.environ.get("BDA_OUTPUT_DIR", "/output"))
out.mkdir(parents=True, exist_ok=True)
pdb = out / "backbone_001.pdb"
pdb.write_text("REMARK BDA stub RFdiffusion output\nEND\n")
print(json.dumps({"backbone_pdbs": [str(pdb)]}))
