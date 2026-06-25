import csv
import hashlib
import io
import json
from pathlib import Path

from fastapi import HTTPException

from ..config import ARTIFACTS_ROOT, STRUCTURES_ROOT, UPLOADS_ROOT

SUPPORTED_ARTIFACT_FORMATS = {
    ".pdb": "pdb",
    ".cif": "mmcif",
    ".mmcif": "mmcif",
    ".fasta": "fasta",
    ".fa": "fasta",
    ".a3m": "a3m",
    ".csv": "csv",
    ".json": "json",
    ".zip": "zip",
    ".txt": "txt",
}

FORMAT_MEDIA_TYPES = {
    "pdb": "chemical/x-pdb",
    "mmcif": "chemical/x-mmcif",
    "fasta": "text/plain",
    "a3m": "text/plain",
    "csv": "text/csv",
    "json": "application/json",
    "zip": "application/zip",
    "txt": "text/plain",
}


def ensure_artifact_dirs() -> None:
    for path in (ARTIFACTS_ROOT, UPLOADS_ROOT, STRUCTURES_ROOT):
        path.mkdir(parents=True, exist_ok=True)


def parse_pdb_metadata(content: str) -> dict:
    chains: set[str] = set()
    residues: set[tuple[str, str, str]] = set()
    atom_count = 0
    for line in content.splitlines():
        if line.startswith("ATOM") or line.startswith("HETATM"):
            atom_count += 1
            if line.startswith("ATOM") and len(line) >= 27:
                chain = line[21].strip() or "_"
                res_seq = line[22:26].strip()
                insertion_code = line[26].strip()
                if not res_seq:
                    continue
                chains.add(chain)
                residues.add((chain, res_seq, insertion_code))
    return {
        "atom_count": atom_count,
        "chain_count": len(chains) or 1,
        "chains": sorted(chains),
        "residue_count": len(residues),
    }


def artifact_format_for_filename(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    artifact_format = SUPPORTED_ARTIFACT_FORMATS.get(suffix)
    if artifact_format is None:
        raise HTTPException(status_code=400, detail="unsupported_artifact_format")
    return artifact_format


def media_type_for_format(artifact_format: str) -> str:
    return FORMAT_MEDIA_TYPES.get(artifact_format, "application/octet-stream")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_fasta_metadata(content: str) -> dict:
    sequence_count = 0
    residue_count = 0
    current: list[str] = []
    lengths: list[int] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(">"):
            if current:
                length = sum(len(part) for part in current)
                lengths.append(length)
                residue_count += length
                current = []
            sequence_count += 1
        else:
            current.append(stripped)
    if current:
        length = sum(len(part) for part in current)
        lengths.append(length)
        residue_count += length
    return {
        "sequence_count": sequence_count or (1 if residue_count else 0),
        "residue_count": residue_count,
        "sequence_lengths": lengths[:20],
    }


def parse_csv_metadata(content: str) -> dict:
    reader = csv.reader(io.StringIO(content))
    try:
        headers = next(reader)
    except StopIteration:
        headers = []
    rows_preview = []
    row_count = 0
    for row in reader:
        row_count += 1
        if len(rows_preview) < 5:
            rows_preview.append(row)
    return {
        "columns": headers,
        "row_count": row_count,
        "preview_rows": rows_preview,
    }


def infer_artifact_metadata(path: Path, artifact_format: str) -> dict:
    if artifact_format in {"pdb", "mmcif"}:
        return parse_pdb_metadata(path.read_text(encoding="utf-8", errors="replace"))
    if artifact_format in {"fasta", "a3m"}:
        return parse_fasta_metadata(path.read_text(encoding="utf-8", errors="replace"))
    if artifact_format == "csv":
        return parse_csv_metadata(path.read_text(encoding="utf-8", errors="replace"))
    if artifact_format == "json":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"valid_json": False}
        if isinstance(payload, dict):
            return {"valid_json": True, "top_level_type": "object", "keys": list(payload.keys())[:30]}
        if isinstance(payload, list):
            return {"valid_json": True, "top_level_type": "array", "length": len(payload)}
        return {"valid_json": True, "top_level_type": type(payload).__name__}
    return {}


def preview_artifact(path: Path, artifact_format: str, max_rows: int = 20, max_chars: int = 8000) -> dict:
    if artifact_format == "zip":
        return {"preview_type": "none", "reason": "zip_preview_not_supported"}
    text = path.read_text(encoding="utf-8", errors="replace")
    if artifact_format == "csv":
        reader = csv.DictReader(io.StringIO(text))
        rows = []
        for row in reader:
            rows.append(row)
            if len(rows) >= max_rows:
                break
        return {
            "preview_type": "table",
            "columns": reader.fieldnames or [],
            "rows": rows,
        }
    if artifact_format == "json":
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            return {"preview_type": "text", "text": text[:max_chars], "error": f"invalid_json:{exc.msg}"}
        return {"preview_type": "json", "value": payload}
    return {"preview_type": "text", "text": text[:max_chars]}


def resolve_artifact_path(relative_path: str) -> Path:
    candidate = (ARTIFACTS_ROOT / relative_path).resolve()
    if not str(candidate).startswith(str(ARTIFACTS_ROOT.resolve())):
        raise HTTPException(status_code=400, detail="invalid_artifact_path")
    if not candidate.exists():
        raise HTTPException(status_code=404, detail="artifact_not_found")
    return candidate


def candidate_structure_path(structure_file_path: str | None, complex_file_path: str | None) -> str | None:
    return complex_file_path or structure_file_path
