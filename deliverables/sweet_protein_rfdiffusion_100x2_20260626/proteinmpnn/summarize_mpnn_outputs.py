#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def read_fasta(path: Path) -> list[tuple[str, str]]:
    records: list[tuple[str, str]] = []
    header: str | None = None
    chunks: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(">"):
            if header is not None:
                records.append((header, "".join(chunks)))
            header = line[1:]
            chunks = []
        else:
            chunks.append(line)
    if header is not None:
        records.append((header, "".join(chunks)))
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seq-dir", required=True)
    parser.add_argument("--out-fasta", required=True)
    parser.add_argument("--out-manifest", required=True)
    args = parser.parse_args()

    seq_dir = Path(args.seq_dir)
    out_fasta = Path(args.out_fasta)
    out_manifest = Path(args.out_manifest)
    out_fasta.parent.mkdir(parents=True, exist_ok=True)

    if not seq_dir.is_dir():
        raise SystemExit(f"[ERROR] Missing ProteinMPNN sequence directory: {seq_dir}")

    manifest: list[dict[str, object]] = []
    with out_fasta.open("w", encoding="utf-8") as handle:
        for fasta in sorted(seq_dir.glob("*.fa")) + sorted(seq_dir.glob("*.fasta")):
            records = read_fasta(fasta)
            if len(records) <= 1:
                continue
            backbone = fasta.stem
            for index, (header, sequence) in enumerate(records[1:], start=1):
                design_id = f"{backbone}_mpnn_seq{index}"
                handle.write(f">{design_id}\n")
                for start in range(0, len(sequence), 60):
                    handle.write(sequence[start:start + 60] + "\n")
                manifest.append({
                    "design_id": design_id,
                    "backbone": backbone,
                    "source_fasta": str(fasta),
                    "source_header": header,
                    "sequence_index": index,
                    "sequence_length": len(sequence),
                })

    out_manifest.write_text(json.dumps({
        "sequence_count": len(manifest),
        "records": manifest,
    }, indent=2), encoding="utf-8")
    print(f"[DONE] Wrote {len(manifest)} designed sequences to {out_fasta}")
    print(f"[DONE] Wrote manifest to {out_manifest}")


if __name__ == "__main__":
    main()
