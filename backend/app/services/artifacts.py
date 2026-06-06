import re
from pathlib import Path

from fastapi import HTTPException

from ..config import ARTIFACTS_ROOT, STRUCTURES_ROOT, UPLOADS_ROOT

PDB_ATOM_RE = re.compile(
    r"^ATOM\s+\d+\s+\S+\s+(\S+)\s+(\d+)",
    re.MULTILINE,
)


def ensure_artifact_dirs() -> None:
    for path in (ARTIFACTS_ROOT, UPLOADS_ROOT, STRUCTURES_ROOT):
        path.mkdir(parents=True, exist_ok=True)


def parse_pdb_metadata(content: str) -> dict:
    chains: set[str] = set()
    residues: set[tuple[str, str]] = set()
    atom_count = 0
    for line in content.splitlines():
        if line.startswith("ATOM") or line.startswith("HETATM"):
            atom_count += 1
            match = PDB_ATOM_RE.match(line)
            if match:
                chain = match.group(1)
                res_seq = match.group(2)
                chains.add(chain)
                residues.add((chain, res_seq))
    return {
        "atom_count": atom_count,
        "chain_count": len(chains) or 1,
        "chains": sorted(chains),
        "residue_count": len(residues),
    }


def resolve_artifact_path(relative_path: str) -> Path:
    candidate = (ARTIFACTS_ROOT / relative_path).resolve()
    if not str(candidate).startswith(str(ARTIFACTS_ROOT.resolve())):
        raise HTTPException(status_code=400, detail="invalid_artifact_path")
    if not candidate.exists():
        raise HTTPException(status_code=404, detail="artifact_not_found")
    return candidate


def candidate_structure_path(structure_file_path: str | None, complex_file_path: str | None) -> str | None:
    return complex_file_path or structure_file_path
