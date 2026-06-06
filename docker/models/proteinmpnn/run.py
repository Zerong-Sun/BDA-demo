#!/usr/bin/env python3
"""Stub ProteinMPNN runner for BDA integration testing."""
import json
import os
import sys
from pathlib import Path

output_dir = Path(os.environ.get("BDA_OUTPUT_DIR", "/output"))
output_dir.mkdir(parents=True, exist_ok=True)

fasta = output_dir / "designed.fasta"
fasta.write_text(">design_1\nACDEFGHIKLMNPQRSTVWY\n")

manifest = {"sequences": [str(fasta)], "model": "ProteinMPNN", "status": "completed"}
(output_dir / "manifest.json").write_text(json.dumps(manifest))
print(json.dumps(manifest))
sys.exit(0)
