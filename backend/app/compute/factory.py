from __future__ import annotations

import base64
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

from ..compute.adapter import ComputeAdapter, JobHandle, JobSpec, JobStatus
from ..settings import REPO_ROOT


class DemoComputeAdapter:
    def render_script(self, job: JobSpec) -> str:
        return "\n".join([
            "#!/bin/bash",
            f"# Demo compute preview for {job.job_id}",
            "echo 'Compute not connected. Set BDA_COMPUTE_MODE=remote_lsf to submit to LSF.'",
            "",
        ])

    def submit(self, job: JobSpec) -> JobHandle:
        return JobHandle(job_id=job.job_id, external_id=f"demo-{job.job_id}")

    def status(self, job_id: str, external_id: str | None = None) -> JobStatus:
        return JobStatus(
            job_id=job_id,
            status="blocked",
            logs="Compute not connected (demo mode). Set BDA_COMPUTE_MODE=docker to enable.",
        )

    def cancel(self, job_id: str, external_id: str | None = None) -> bool:
        return False

    def logs(self, job_id: str, external_id: str | None = None, tail: int = 100) -> str:
        return "Compute not connected (demo mode)."


class LocalDockerAdapter:
    def __init__(self) -> None:
        import docker

        from ..settings import get_settings

        settings = get_settings()
        self._client = docker.from_env() if settings.bda_docker_host == "unix:///var/run/docker.sock" else docker.DockerClient(base_url=settings.bda_docker_host)

    def render_script(self, job: JobSpec) -> str:
        env = {
            "BDA_JOB_ID": job.job_id,
            "BDA_INPUT_MANIFEST": "/input/manifest.json",
            "BDA_OUTPUT_DIR": "/output",
            **(job.env or {}),
        }
        env_flags = " ".join(f"-e {shlex.quote(str(key))}={shlex.quote(str(value))}" for key, value in sorted(env.items()))
        volume_flags = []
        if job.input_dir:
            volume_flags.append(f"-v {shlex.quote(job.input_dir)}:/input:ro")
        if job.output_dir:
            volume_flags.append(f"-v {shlex.quote(job.output_dir)}:/output:rw")
        if job.work_dir:
            volume_flags.append(f"-v {shlex.quote(job.work_dir)}:/work:rw")
        return "\n".join([
            "#!/bin/bash",
            f"# Local Docker preview for {job.job_id}",
            "docker run --rm \\",
            f"  {env_flags} \\",
            f"  {' '.join(volume_flags)} \\",
            f"  {shlex.quote(job.container_image)} {job.command}",
            "",
        ])

    def submit(self, job: JobSpec) -> JobHandle:
        import docker

        env = {
            "BDA_JOB_ID": job.job_id,
            "BDA_INPUT_MANIFEST": "/input/manifest.json",
            "BDA_OUTPUT_DIR": "/output",
            **(job.env or {}),
        }
        run_kwargs: dict = {
            "image": job.container_image,
            "command": shlex.split(job.command) if job.command else None,
            "detach": True,
            "remove": False,
            "environment": env,
        }
        volumes = {}
        if job.input_dir:
            volumes[job.input_dir] = {"bind": "/input", "mode": "ro"}
        if job.output_dir:
            volumes[job.output_dir] = {"bind": "/output", "mode": "rw"}
        if job.work_dir:
            volumes[job.work_dir] = {"bind": "/work", "mode": "rw"}
        if volumes:
            run_kwargs["volumes"] = volumes
        if env.get("BDA_GPU") == "1":
            run_kwargs["device_requests"] = [docker.types.DeviceRequest(count=-1, capabilities=[["gpu"]])]

        try:
            container = self._client.containers.run(**run_kwargs)
        except docker.errors.ImageNotFound as exc:
            raise RuntimeError(f"container_image_not_found:{job.container_image}") from exc

        return JobHandle(job_id=job.job_id, external_id=container.id)

    def status(self, job_id: str, external_id: str | None = None) -> JobStatus:
        if not external_id:
            return JobStatus(job_id=job_id, status="not_found")
        container = self._client.containers.get(external_id)
        state = container.attrs.get("State", {})
        status_map = {
            "created": "queued",
            "running": "running",
            "exited": "completed" if state.get("ExitCode") == 0 else "failed",
            "dead": "failed",
        }
        status = status_map.get(container.status, container.status)
        logs = container.logs(tail=200).decode("utf-8", errors="replace")
        error = state.get("Error") if status == "failed" else None
        return JobStatus(job_id=job_id, status=status, logs=logs, error_message=error)

    def cancel(self, job_id: str, external_id: str | None = None) -> bool:
        if not external_id:
            return False
        container = self._client.containers.get(external_id)
        container.stop(timeout=10)
        return True

    def logs(self, job_id: str, external_id: str | None = None, tail: int = 100) -> str:
        if not external_id:
            return ""
        container = self._client.containers.get(external_id)
        return container.logs(tail=tail).decode("utf-8", errors="replace")


class LocalProcessAdapter:
    """Run built-in stub model runners directly for local development and tests."""

    _IMAGE_DIRS = {
        "bda/rfdiffusion": "rfdiffusion",
        "bda/proteinmpnn": "proteinmpnn",
        "bda/alphafold2": "alphafold2",
        "bda/rosetta": "rosetta",
    }

    def __init__(self) -> None:
        self._statuses: dict[str, JobStatus] = {}

    def render_script(self, job: JobSpec) -> str:
        env = {
            "BDA_JOB_ID": job.job_id,
            "BDA_INPUT_MANIFEST": str(Path(job.input_dir or "") / "manifest.json"),
            "BDA_OUTPUT_DIR": str(Path(job.output_dir or "")),
            **(job.env or {}),
        }
        exports = [f"export {key}={shlex.quote(str(value))}" for key, value in sorted(env.items())]
        return "\n".join([
            "#!/bin/bash",
            f"# Local process preview for {job.job_id}",
            *exports,
            job.command or "python run.py",
            "",
        ])

    def _runner_dir(self, image: str) -> Path:
        image_name = image.split(":", 1)[0]
        model_dir = self._IMAGE_DIRS.get(image_name)
        if not model_dir:
            raise RuntimeError(f"local_runner_not_available:{image}")
        path = REPO_ROOT.parent / "docker" / "models" / model_dir
        if not (path / "run.py").exists():
            raise RuntimeError(f"local_runner_missing:{model_dir}")
        return path

    def submit(self, job: JobSpec) -> JobHandle:
        runner_dir = self._runner_dir(job.container_image)
        env = {
            "BDA_JOB_ID": job.job_id,
            "BDA_INPUT_MANIFEST": str(Path(job.input_dir or "") / "manifest.json"),
            "BDA_OUTPUT_DIR": str(Path(job.output_dir or runner_dir)),
            **(job.env or {}),
        }
        command = shlex.split(job.command) if job.command else [sys.executable, "run.py"]
        if command and command[0] == "python":
            command[0] = sys.executable
        try:
            proc = subprocess.run(
                command,
                cwd=runner_dir,
                env={**os.environ, **env},
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except Exception as exc:  # noqa: BLE001 - adapter reports failure as job status
            self._statuses[job.job_id] = JobStatus(job_id=job.job_id, status="failed", error_message=str(exc))
            return JobHandle(job_id=job.job_id, external_id=f"local-{job.job_id}")

        status = "completed" if proc.returncode == 0 else "failed"
        logs = "\n".join(part for part in (proc.stdout, proc.stderr) if part)
        self._statuses[job.job_id] = JobStatus(
            job_id=job.job_id,
            status=status,
            logs=logs,
            error_message=None if status == "completed" else f"exit_code:{proc.returncode}",
        )
        return JobHandle(job_id=job.job_id, external_id=f"local-{job.job_id}")

    def status(self, job_id: str, external_id: str | None = None) -> JobStatus:
        return self._statuses.get(job_id) or JobStatus(job_id=job_id, status="not_found")

    def cancel(self, job_id: str, external_id: str | None = None) -> bool:
        return False

    def logs(self, job_id: str, external_id: str | None = None, tail: int = 100) -> str:
        status = self._statuses.get(job_id)
        if not status:
            return ""
        lines = status.logs.splitlines()
        return "\n".join(lines[-tail:])


class RemoteLsfAdapter:
    """Stage jobs over SSH and execute trusted wrappers through IBM Spectrum LSF."""

    _SAFE_JOB_ID = re.compile(r"^job_[A-Za-z0-9_-]+$")
    _LSF_STATUS = {
        "PEND": "queued",
        "WAIT": "queued",
        "PROV": "queued",
        "RUN": "running",
        "DONE": "completed",
        "EXIT": "failed",
        "PSUSP": "queued",
        "USUSP": "queued",
        "SSUSP": "queued",
        "UNKWN": "running",
        "ZOMBI": "failed",
    }

    def __init__(self) -> None:
        from ..settings import get_settings

        settings = get_settings()
        self._host = settings.bda_lsf_ssh_host
        self._remote_root = settings.bda_lsf_remote_root.rstrip("/")
        self._cpu_queue = settings.bda_lsf_default_cpu_queue
        self._gpu_queue = settings.bda_lsf_default_gpu_queue
        self._connect_timeout = settings.bda_lsf_connect_timeout_seconds
        self._plugin_commands = settings.lsf_plugin_commands
        self._ssh_password = settings.bda_lsf_ssh_password

    def _ssh_args(self, *, batch_mode: bool = True) -> list[str]:
        return [
            "ssh",
            "-o", f"BatchMode={'yes' if batch_mode else 'no'}",
            "-o", "NumberOfPasswordPrompts=1",
            "-o", f"ConnectTimeout={self._connect_timeout}",
            self._host,
        ]

    def _remote_job_dir(self, job_id: str) -> str:
        if not self._SAFE_JOB_ID.fullmatch(job_id):
            raise RuntimeError("invalid_remote_job_id")
        return f"{self._remote_root}/jobs/{job_id}"

    def _run_ssh(
        self,
        command: str,
        *,
        input_data: bytes | None = None,
        timeout: int = 30,
        check: bool = True,
    ) -> subprocess.CompletedProcess[bytes]:
        password = getattr(self, "_ssh_password", "")
        if password:
            return self._run_ssh_with_password(command, input_data=input_data, timeout=timeout, check=check)
        try:
            return subprocess.run(
                [*self._ssh_args(), command],
                input=input_data,
                capture_output=True,
                timeout=timeout,
                check=check,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise RuntimeError(f"remote_lsf_ssh_failed:{exc}") from exc

    def _run_ssh_with_password(
        self,
        command: str,
        *,
        input_data: bytes | None = None,
        timeout: int = 30,
        check: bool = True,
    ) -> subprocess.CompletedProcess[bytes]:
        local_input_path: str | None = None
        try:
            ssh_command = shlex.join([*self._ssh_args(batch_mode=False), command])
            local_command = ssh_command
            if input_data is not None:
                with tempfile.NamedTemporaryFile(delete=False) as handle:
                    handle.write(input_data)
                    local_input_path = handle.name
                local_command = f"cat {shlex.quote(local_input_path)} | {ssh_command}"
            expect_script = """
log_user 1
set timeout $env(BDA_LSF_EXPECT_TIMEOUT)
set pass $env(BDA_LSF_SSH_PASSWORD)
spawn -noecho sh -c $env(BDA_LSF_LOCAL_COMMAND)
expect {
  -re "(?i)password:" {
    log_user 0
    send -- "$pass\\r"
    log_user 1
    exp_continue
  }
  eof
}
set result [wait]
exit [lindex $result 3]
"""
            env = {
                **os.environ,
                "BDA_LSF_SSH_PASSWORD": str(getattr(self, "_ssh_password", "")),
                "BDA_LSF_EXPECT_TIMEOUT": str(timeout),
                "BDA_LSF_LOCAL_COMMAND": local_command,
            }
            result = subprocess.run(
                ["expect", "-c", expect_script],
                capture_output=True,
                timeout=timeout + 5,
                check=False,
                env=env,
            )
            if check and result.returncode != 0:
                raise subprocess.CalledProcessError(
                    result.returncode,
                    ["ssh", self._host, command],
                    output=result.stdout,
                    stderr=result.stderr,
                )
            return subprocess.CompletedProcess(
                args=["ssh", self._host, command],
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise RuntimeError(f"remote_lsf_ssh_failed:{exc}") from exc
        finally:
            if local_input_path:
                try:
                    os.unlink(local_input_path)
                except OSError:
                    pass

    def _ssh_error_summary(self, stderr: str) -> str:
        lines = [
            line.strip()
            for line in stderr.splitlines()
            if line.strip() and not line.startswith("** WARNING:")
        ]
        cleaned = "\n".join(lines)
        if "Permission denied" in cleaned:
            return "cluster_ssh_permission_denied"
        return cleaned or "remote_lsf_command_failed"

    def _manifest_payload(self, job: JobSpec) -> dict:
        if not job.input_dir:
            return {}
        manifest_path = Path(job.input_dir) / "manifest.json"
        if not manifest_path.exists():
            return {}
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _staged_input_name(self, manifest: dict) -> str:
        for item in manifest.get("inputs") or []:
            if item.get("port") != "target_structure":
                continue
            path = str(item.get("path") or "")
            name = Path(path).name
            if name:
                return name
        return "input.pdb"

    def _staged_input_names(self, manifest: dict, *, port: str, formats: set[str] | None = None) -> list[str]:
        names: list[str] = []
        for item in manifest.get("inputs") or []:
            if item.get("port") != port:
                continue
            if formats and str(item.get("format") or "").lower() not in formats:
                continue
            path = str(item.get("path") or "")
            name = Path(path).name
            if name:
                names.append(name)
        return names

    def _rfdiffusion_arg(self, key: str, value: object) -> str | None:
        if value is None or value == "":
            return None
        if key == "contigmap.provide_seq" and isinstance(value, str):
            match = re.fullmatch(r"\[\s*(\d+\s*,\s*)+\d+\s*\]", value)
            if match:
                values = [item.strip() for item in value.strip()[1:-1].split(",")]
                value = "[" + ",".join(f"{item}-{item}" for item in values) + "]"
        elif key == "contigmap.provide_seq" and isinstance(value, list):
            normalized: list[str] = []
            for item in value:
                text = str(item)
                normalized.append(text if "-" in text else f"{text}-{text}")
            value = "[" + ",".join(normalized) + "]"
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        elif isinstance(value, (dict, list)):
            rendered = json.dumps(value, separators=(",", ":"))
        else:
            rendered = str(value)
        if any(char in rendered for char in "[] ,"):
            return f"{shlex.quote(f'{key}={rendered}')}"
        return f"{key}={shlex.quote(rendered)}"

    def _render_rfdiffusion_lsf_script(self, job: JobSpec) -> str:
        manifest = self._manifest_payload(job)
        parameters = manifest.get("parameters") or {}
        gpu = job.env.get("BDA_GPU") == "1"
        partial_t = int(parameters.get("diffuser.partial_T") or 0)
        default_queue = "8v100-32-sc" if partial_t > 0 else "4v100-16-e5"
        queue = job.queue_name or job.env.get("BDA_LSF_QUEUE") or default_queue
        resource_requirement = job.resource_requirement or job.env.get("BDA_LSF_RESOURCE") or "span[ptile=1]"
        gpu_requirement = job.gpu_requirement or job.env.get("BDA_LSF_GPU") or "num=1"
        remote_dir = self._remote_job_dir(job.job_id)
        input_name = self._staged_input_name(manifest)
        work_input = "rfdiffusion_input.pdb"
        output_prefix = str(parameters.get("inference.output_prefix") or "rfdiffusion_design")
        output_prefix = Path(output_prefix).name or "rfdiffusion_design"
        run_args = [
            f"inference.input_pdb=./{work_input}",
            self._rfdiffusion_arg("contigmap.contigs", parameters.get("contigmap.contigs")),
            self._rfdiffusion_arg("ppi.hotspot_res", parameters.get("ppi.hotspot_res")),
            self._rfdiffusion_arg("contigmap.provide_seq", parameters.get("contigmap.provide_seq")),
            self._rfdiffusion_arg("inference.num_designs", parameters.get("inference.num_designs") or 100),
            f"inference.output_prefix=../output/{shlex.quote(output_prefix)}",
            self._rfdiffusion_arg("diffuser.partial_T", parameters.get("diffuser.partial_T")),
            self._rfdiffusion_arg("diffuser.T", parameters.get("diffuser.T")),
            self._rfdiffusion_arg("denoiser.noise_scale_ca", parameters.get("denoiser.noise_scale_ca")),
            self._rfdiffusion_arg("denoiser.noise_scale_frame", parameters.get("denoiser.noise_scale_frame")),
            self._rfdiffusion_arg("contigmap.inpaint_seq", parameters.get("contigmap.inpaint_seq")),
            self._rfdiffusion_arg("contigmap.inpaint_str", parameters.get("contigmap.inpaint_str")),
            self._rfdiffusion_arg("inference.ckpt_override_path", parameters.get("inference.ckpt_override_path")),
            self._rfdiffusion_arg("inference.symmetry", parameters.get("inference.symmetry")),
            self._rfdiffusion_arg("potentials.guiding_potentials", parameters.get("potentials.guiding_potentials")),
            self._rfdiffusion_arg("potentials.guide_scale", parameters.get("potentials.guide_scale")),
        ]
        run_args = [arg for arg in run_args if arg]
        run_command = " \\\n".join(run_args) + " \\"
        collect_script = f"""
python - <<'PY' >> ../logs/$LSB_JOBID.log 2>&1
import json
from pathlib import Path

output_dir = Path("../output").resolve()
source_manifest = json.loads(Path("../input/manifest.json").read_text(encoding="utf-8"))
prefix = {output_prefix!r}
backbones = sorted(output_dir.glob(f"{{prefix}}*.pdb"))
if not backbones:
    raise RuntimeError(f"RFdiffusion produced no PDB files for prefix {{prefix}}")
route = (source_manifest.get("parameters") or {{}}).get("scaffold")
outputs = {{
    "backbone_set": [
        {{
            "path": path.name,
            "format": "pdb",
            "artifact_type": "backbone_set",
            "display_name": path.name,
            "metadata": {{"design_index": index, "route": route}},
        }}
        for index, path in enumerate(backbones)
    ],
    "run_record": [
        {{
            "path": "rfdiffusion_run.json",
            "format": "json",
            "artifact_type": "run_record",
            "display_name": "rfdiffusion_run.json",
        }}
    ],
}}
(output_dir / "rfdiffusion_run.json").write_text(
    json.dumps({{
        "backbone_count": len(backbones),
        "parameters": source_manifest.get("parameters") or {{}},
        "inputs": source_manifest.get("inputs") or [],
        "native_lsf_template": "qm-scripts/rfd",
    }}, indent=2),
    encoding="utf-8",
)
(output_dir / "manifest.json").write_text(
    json.dumps({{"outputs": outputs, "metrics": {{"backbone_count": len(backbones)}}}}, indent=2),
    encoding="utf-8",
)
PY"""
        directives = [
            "#!/bin/bash",
            "",
            f"#BSUB -J RFdiffusion_{job.job_id.removeprefix('job_')[:10]}",
            f"#BSUB -q {queue}",
            "#BSUB -n 1",
        ]
        if gpu:
            directives.append(f'#BSUB -gpu "{gpu_requirement}"')
        directives.extend([
            f'#BSUB -R "{resource_requirement}"',
            "#BSUB -o %J.out",
            "#BSUB -e %J.err",
            "",
            f"cd {shlex.quote(remote_dir)}",
            "mkdir -p output work logs",
            f"cp input/{shlex.quote(input_name)} work/{work_input}",
            "",
            "source activate /work/bme-liz/miniconda3/envs/SE3nv-gpu",
            "",
            "cd work",
            "/work/bme-liz/software/RFdiffusion/scripts/run_inference.py \\",
            run_command,
            "> ../logs/$LSB_JOBID.log 2>&1",
            collect_script.strip(),
        ])
        return "\n".join(directives) + "\n"

    def _render_proteinmpnn_lsf_script(self, job: JobSpec) -> str:
        manifest = self._manifest_payload(job)
        parameters = manifest.get("parameters") or {}
        queue = job.queue_name or job.env.get("BDA_LSF_QUEUE") or "4v100-16-e5"
        resource_requirement = job.resource_requirement or job.env.get("BDA_LSF_RESOURCE") or "span[ptile=64]"
        gpu_requirement = job.gpu_requirement or job.env.get("BDA_LSF_GPU") or "num=1"
        remote_dir = self._remote_job_dir(job.job_id)
        pdb_names = self._staged_input_names(manifest, port="backbone_set", formats={"pdb"})
        num_seq = int(parameters.get("num_seq_per_target") or 5)
        batch_size = int(parameters.get("batch_size") or 1)
        sampling_temp = str(parameters.get("sampling_temp") or "0.2")
        chain_to_design = str(parameters.get("pdb_path_chains") or parameters.get("chain_to_design") or "A")
        seed = int(parameters.get("seed") or 37)
        pack_side_chains = bool(parameters.get("pack_side_chains", True))
        pdb_copy_lines = "\n".join(
            f"cp input/{shlex.quote(name)} work/pdb/{shlex.quote(name)}"
            for name in pdb_names
        ) or "find input -maxdepth 1 -type f -name '*.pdb' -exec cp {} work/pdb/ \\;"
        collect_script = """
python - <<'PY' >> logs/$LSB_JOBID.log 2>&1
import csv
import json
import re
from pathlib import Path

output_dir = Path("output").resolve()
seq_dir = output_dir / "seqs"
packed_dir = output_dir / "packed"
combined_fasta = output_dir / "sweetprotein_mpnn5_designs.fasta"
score_csv = output_dir / "proteinmpnn_scores.csv"
records = []

def read_fasta(path):
    header = None
    chunks = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                if header is not None:
                    yield header, "".join(chunks)
                header = line[1:]
                chunks = []
            else:
                chunks.append(line)
    if header is not None:
        yield header, "".join(chunks)

score_re = re.compile(r"(?:score|global_score)=(-?\\d+(?:\\.\\d+)?)")
combined_fasta.parent.mkdir(parents=True, exist_ok=True)
with combined_fasta.open("w", encoding="utf-8") as fasta_out:
    for fasta in sorted(seq_dir.glob("*.fa")) + sorted(seq_dir.glob("*.fasta")):
        backbone = fasta.stem
        for index, (header, sequence) in enumerate(list(read_fasta(fasta))[1:], start=1):
            design_id = f"{backbone}_mpnn_seq{index}"
            fasta_out.write(f">{design_id}\\n")
            for start in range(0, len(sequence), 60):
                fasta_out.write(sequence[start:start + 60] + "\\n")
            match = score_re.search(header)
            records.append({
                "design_id": design_id,
                "backbone": backbone,
                "source_fasta": fasta.name,
                "source_header": header,
                "sequence_index": index,
                "sequence_length": len(sequence),
                "mpnn_score": float(match.group(1)) if match else None,
            })

with score_csv.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=["design_id", "backbone", "sequence_index", "sequence_length", "mpnn_score"])
    writer.writeheader()
    for record in records:
        writer.writerow({key: record.get(key) for key in writer.fieldnames})

(output_dir / "proteinmpnn_run.json").write_text(
    json.dumps({
        "sequence_count": len(records),
        "parameters": json.loads(Path("input/manifest.json").read_text(encoding="utf-8")).get("parameters") or {},
        "records": records,
    }, indent=2),
    encoding="utf-8",
)
(output_dir / "manifest.json").write_text(
    json.dumps({
        "outputs": {
            "sequence_set": [{
                "path": "sweetprotein_mpnn5_designs.fasta",
                "format": "fasta",
                "artifact_type": "sequence_set",
                "display_name": "sweetprotein_mpnn5_designs.fasta",
                "metadata": {"sequence_count": len(records), "source_port": "sequence_set"},
            }],
            "packed_structure": [
                {
                    "path": str(path.relative_to(output_dir)),
                    "format": "pdb",
                    "artifact_type": "packed_structure",
                    "display_name": path.name,
                    "metadata": {"candidate_id": path.stem, "source_port": "packed_structure"},
                }
                for path in sorted(packed_dir.glob("*.pdb"))
            ],
            "score_table": [{
                "path": "proteinmpnn_scores.csv",
                "format": "csv",
                "artifact_type": "score_table",
                "display_name": "proteinmpnn_scores.csv",
            }],
            "run_manifest": [{
                "path": "proteinmpnn_run.json",
                "format": "json",
                "artifact_type": "manifest",
                "display_name": "proteinmpnn_run.json",
            }],
        },
        "metrics": {"designed": len(records), "backbones": len(list(Path("work/pdb").glob("*.pdb")))},
    }, indent=2),
    encoding="utf-8",
)
if not records:
    raise RuntimeError("ProteinMPNN produced no designed sequences")
PY"""
        directives = [
            "#!/bin/bash",
            "",
            f"#BSUB -J ProteinMPNN_{job.job_id.removeprefix('job_')[:10]}",
            f"#BSUB -q {queue}",
            "#BSUB -n 1",
            f'#BSUB -gpu "{gpu_requirement}"',
            f'#BSUB -R "{resource_requirement}"',
            "#BSUB -o logs/%J.out",
            "#BSUB -e logs/%J.err",
            "",
            "set -Eeuo pipefail",
            f"cd {shlex.quote(remote_dir)}",
            "mkdir -p output work/pdb logs",
            pdb_copy_lines,
            "backbone_count=$(find work/pdb -maxdepth 1 -type f -name '*.pdb' | wc -l | tr -d ' ')",
            "if [[ \"$backbone_count\" == \"0\" ]]; then echo '[ERROR] No backbone PDBs staged for ProteinMPNN' >&2; exit 1; fi",
            "echo \"[INFO] ProteinMPNN backbones: $backbone_count\"",
            "if [[ -f /work/bme-liz/miniconda3/etc/profile.d/conda.sh ]]; then source /work/bme-liz/miniconda3/etc/profile.d/conda.sh; conda activate mlfold; else source activate /work/bme-liz/miniconda3/envs/mlfold; fi",
            "",
            "python /work/bme-liz/software/proteinmpnn-main/helper_scripts/parse_multiple_chains.py \\",
            "  --input_path work/pdb \\",
            "  --output_path output/parsed_pdbs.jsonl",
            "python /work/bme-liz/software/proteinmpnn-main/helper_scripts/assign_fixed_chains.py \\",
            "  --input_path output/parsed_pdbs.jsonl \\",
            "  --output_path output/assigned_pdbs.jsonl \\",
            f"  --chain_list {shlex.quote(chain_to_design)}",
            "python /work/bme-liz/software/proteinmpnn-main/protein_mpnn_run.py \\",
            "  --jsonl_path output/parsed_pdbs.jsonl \\",
            "  --chain_id_jsonl output/assigned_pdbs.jsonl \\",
            "  --out_folder output \\",
            f"  --num_seq_per_target {num_seq} \\",
            f"  --sampling_temp {shlex.quote(sampling_temp)} \\",
            f"  --seed {seed} \\",
            f"  --batch_size {batch_size} \\",
            f"  --pack_side_chains {1 if pack_side_chains else 0} > logs/$LSB_JOBID.log 2>&1",
            collect_script.strip(),
            "echo '[DONE] ProteinMPNN finished.'",
        ]
        return "\n".join(directives) + "\n"

    def _render_alphafold2_lsf_script(self, job: JobSpec) -> str:
        manifest = self._manifest_payload(job)
        parameters = manifest.get("parameters") or {}
        force_cpu = bool(parameters.get("force_cpu")) or job.env.get("BDA_GPU") == "0"
        queue = job.queue_name or job.env.get("BDA_LSF_QUEUE") or (self._cpu_queue if force_cpu else "4v100-16-e5")
        cpu_count = max(1, int(job.env.get("BDA_CPU_COUNT") or parameters.get("jackhmmer_n_cpu") or 8))
        resource_requirement = job.resource_requirement or job.env.get("BDA_LSF_RESOURCE") or "span[ptile=1]"
        gpu_requirement = job.gpu_requirement or job.env.get("BDA_LSF_GPU") or "num=1"
        remote_dir = self._remote_job_dir(job.job_id)
        pdb_names = (
            self._staged_input_names(manifest, port="packed_structure", formats={"pdb"})
            or self._staged_input_names(manifest, port="structure", formats={"pdb"})
            or self._staged_input_names(manifest, port="backbone_set", formats={"pdb"})
        )
        fasta_names = self._staged_input_names(manifest, port="sequence_set", formats={"fasta", "fa"})
        models = int(parameters.get("superfold_models") or 4)
        max_recycle = int(parameters.get("max_recycle") or parameters.get("max_recycles") or 5)
        use_pdb_input = bool(pdb_names) or str(parameters.get("superfold_input_mode") or "").lower() in {
            "pdb",
            "packed_pdb",
            "packed_structure",
        }
        pdb_copy_lines = "\n".join(
            f"cp input/{shlex.quote(name)} work/input_pdb/{shlex.quote(name)}"
            for name in pdb_names
        ) or "find input -maxdepth 1 -type f -name '*.pdb' -exec cp {} work/input_pdb/ \\;"
        fasta_copy_lines = "\n".join(
            f"cp input/{shlex.quote(name)} work/input_fasta/{shlex.quote(name)}"
            for name in fasta_names
        ) or "find input -maxdepth 1 \\( -name '*.fa' -o -name '*.fasta' \\) -exec cp {} work/input_fasta/ \\;"
        collect_script = """
python - <<'PY' >> logs/$LSB_JOBID.log 2>&1
import csv
import json
import re
from pathlib import Path

output_dir = Path("output").resolve()
records = []
report_scores = {}
report_re = re.compile(
    r"^(?P<name>\\S+)\\s+\\S+\\s+recycles:(?P<recycles>\\d+)\\s+tol:(?P<tol>\\S+)\\s+"
    r"mean_plddt:(?P<plddt>\\S+)\\s+pTMscore:(?P<ptm>\\S+)(?:\\s+rmsd_to_input:(?P<rmsd>\\S+))?"
)

for report in output_dir.rglob("reports.txt"):
    for raw in report.read_text(encoding="utf-8", errors="replace").splitlines():
        match = report_re.search(raw.strip())
        if not match:
            continue
        report_scores[match.group("name")] = {
            "plddt": float(match.group("plddt")),
            "ptm": float(match.group("ptm")),
            "rmsd_to_input": float(match.group("rmsd")) if match.group("rmsd") else None,
        }

def candidate_name(path):
    name = path.stem
    name = re.sub(r"_model_\\d+_ptm_seed_\\d+_(?:unrelaxed|relaxed|prediction_results)$", "", name)
    for suffix in ("_unrelaxed_rank_001", "_relaxed_rank_001", "_rank_001", "_model_1"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name

def read_json_score(path):
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    values = payload.get("plddt") or payload.get("plddts")
    plddt = None
    if isinstance(values, list) and values:
        plddt = sum(float(value) for value in values) / len(values)
    elif isinstance(values, (int, float)):
        plddt = float(values)
    elif isinstance(payload.get("mean_plddt"), (int, float)):
        plddt = float(payload["mean_plddt"])
    return {
        "plddt": plddt,
        "ptm": payload.get("ptm") or payload.get("pTMscore"),
        "iptm": payload.get("iptm"),
        "pae": payload.get("pae") or payload.get("predicted_aligned_error"),
    }

score_by_candidate = {}
for path in output_dir.rglob("*.json"):
    if "timings" in path.name or path.name in {"manifest.json", "alphafold2_run.json"}:
        continue
    scores = read_json_score(path)
    if any(value is not None for value in scores.values()):
        score_by_candidate.setdefault(candidate_name(path), {}).update(scores)

for pdb_path in sorted(output_dir.rglob("*.pdb")):
    candidate = candidate_name(pdb_path)
    scores = score_by_candidate.get(candidate, {}) or report_scores.get(candidate, {})
    relative = pdb_path.relative_to(output_dir)
    records.append({
        "candidate_id": candidate,
        "path": str(relative),
        "plddt": scores.get("plddt"),
        "ptm": scores.get("ptm"),
        "iptm": scores.get("iptm"),
        "rmsd_to_input": scores.get("rmsd_to_input"),
    })

score_csv = output_dir / "alphafold2_confidence.csv"
with score_csv.open("w", encoding="utf-8", newline="") as handle:
    fieldnames = ["candidate_id", "path", "plddt", "ptm", "iptm", "rmsd_to_input"]
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    for record in records:
        writer.writerow({key: record.get(key) for key in fieldnames})

outputs = {
    "predicted_structure": [
        {
            "path": record["path"],
            "format": "pdb",
            "artifact_type": "predicted_structure",
            "display_name": Path(record["path"]).name,
            "metadata": {
                "candidate_id": record["candidate_id"],
                "plddt": record.get("plddt"),
                "ptm": record.get("ptm"),
                "iptm": record.get("iptm"),
                "rmsd_to_input": record.get("rmsd_to_input"),
                "source_port": "predicted_structure",
            },
        }
        for record in records
    ],
    "score_table": [
        {
            "path": "alphafold2_confidence.csv",
            "format": "csv",
            "artifact_type": "score_table",
            "display_name": "alphafold2_confidence.csv",
            "metadata": {"row_count": len(records), "source_port": "score_table"},
        }
    ],
}
(output_dir / "alphafold2_run.json").write_text(
    json.dumps({
        "folded_count": len(records),
        "parameters": json.loads(Path("input/manifest.json").read_text(encoding="utf-8")).get("parameters") or {},
        "records": records,
    }, indent=2),
    encoding="utf-8",
)
outputs["run_manifest"] = [
    {
        "path": "alphafold2_run.json",
        "format": "json",
        "artifact_type": "manifest",
        "display_name": "alphafold2_run.json",
    }
]
(output_dir / "manifest.json").write_text(
    json.dumps({"outputs": outputs, "metrics": {"folded": len(records)}}, indent=2),
    encoding="utf-8",
)
if not records:
    raise RuntimeError("AlphaFold2/Superfold produced no PDB predictions")
PY"""
        split_script = """
python - <<'PY' >> logs/$LSB_JOBID.log 2>&1
from pathlib import Path
import re

input_dir = Path("work/input_fasta")
single_dir = Path("work/single_fasta")
single_dir.mkdir(parents=True, exist_ok=True)
count = 0
header = None
chunks = []

def flush():
    global count, header, chunks
    if header is None:
        return
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", header.split()[0]).strip("_") or f"sequence_{count+1}"
    out = single_dir / f"{safe}.fasta"
    out.write_text(f">{safe}\\n{''.join(chunks)}\\n", encoding="utf-8")
    count += 1

for fasta in sorted(input_dir.glob("*.fa")) + sorted(input_dir.glob("*.fasta")):
    with fasta.open(encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                flush()
                header = line[1:]
                chunks = []
            else:
                chunks.append(line)
        flush()
        header = None
        chunks = []
print(f"[INFO] AlphaFold2 sequences staged: {count}")
if count == 0:
    raise RuntimeError("No FASTA records staged for AlphaFold2")
PY"""
        directives = [
            "#!/bin/bash",
            "",
            f"#BSUB -J AlphaFold2_{job.job_id.removeprefix('job_')[:10]}",
            f"#BSUB -q {queue}",
            f"#BSUB -n {cpu_count}",
            f'#BSUB -R "{resource_requirement}"',
            "#BSUB -o logs/%J.out",
            "#BSUB -e logs/%J.err",
            "",
            "set -Eeuo pipefail",
            f"cd {shlex.quote(remote_dir)}",
            "mkdir -p output work/input_pdb work/input_fasta work/single_fasta logs",
            "PYTHON_BIN=$(command -v python3 || command -v python)",
            "source deactivate base >/dev/null 2>&1 || true",
            "conda deactivate >/dev/null 2>&1 || true",
            "export CUDA_VISIBLE_DEVICES=\"\"" if force_cpu else "true",
        ]
        if use_pdb_input:
            directives.extend([
                pdb_copy_lines,
                "pdb_count=$(find work/input_pdb -maxdepth 1 -type f -name '*.pdb' | wc -l | tr -d ' ')",
                "echo \"[INFO] AlphaFold2/Superfold PDB inputs staged: $pdb_count\" | tee -a logs/$LSB_JOBID.log",
                "if [[ \"$pdb_count\" == \"0\" ]]; then echo '[ERROR] No PDB records staged for AlphaFold2/Superfold' >&2; exit 1; fi",
                "for pdb_file in work/input_pdb/*.pdb; do",
                "  name=$(basename \"$pdb_file\" .pdb)",
                "  mkdir -p \"output/$name\"",
                f"  /work/bme-liz/software/superfold/superfold \"$pdb_file\" --models {models} --max_recycle {max_recycle} --output_summary --out_dir \"output/$name\" >> logs/$LSB_JOBID.log 2>&1",
                "done",
            ])
        else:
            directives.extend([
                fasta_copy_lines,
                split_script.strip().replace("python - <<'PY'", '"$PYTHON_BIN" - <<\'PY\''),
                "for fasta_file in work/single_fasta/*.fasta; do",
                "  name=$(basename \"$fasta_file\" .fasta)",
                "  mkdir -p \"output/$name\"",
                f"  /work/bme-liz/software/superfold/superfold \"$fasta_file\" --models {models} --max_recycle {max_recycle} --output_summary --out_dir \"output/$name\" >> logs/$LSB_JOBID.log 2>&1",
                "done",
            ])
        directives.extend([
            collect_script.strip().replace("python - <<'PY'", '"$PYTHON_BIN" - <<\'PY\''),
            "echo '[DONE] AlphaFold2/Superfold finished.'",
        ])
        if not force_cpu:
            directives.insert(6, f'#BSUB -gpu "{gpu_requirement}"')
        return "\n".join(directives) + "\n"

    def _render_lsf_script(self, job: JobSpec, trusted_command: str) -> str:
        if job.plugin_id == "plugin_rfdiffusion":
            return self._render_rfdiffusion_lsf_script(job)
        if job.plugin_id == "plugin_proteinmpnn":
            return self._render_proteinmpnn_lsf_script(job)
        if job.plugin_id == "plugin_alphafold2":
            return self._render_alphafold2_lsf_script(job)
        gpu = job.env.get("BDA_GPU") == "1"
        queue = job.queue_name or job.env.get("BDA_LSF_QUEUE") or (self._gpu_queue if gpu else self._cpu_queue)
        cpu_count = max(1, int(job.env.get("BDA_CPU_COUNT", "1")))
        resource_requirement = job.resource_requirement or job.env.get("BDA_LSF_RESOURCE") or "span[ptile=1]"
        gpu_requirement = job.gpu_requirement or job.env.get("BDA_LSF_GPU") or "num=1"
        remote_dir = self._remote_job_dir(job.job_id)
        directives = [
            "#!/bin/bash",
            f"#BSUB -J bda-{job.job_id}",
            f"#BSUB -q {queue}",
            f"#BSUB -n {cpu_count}",
            f'#BSUB -R "{resource_requirement}"',
            "#BSUB -o logs/%J.out",
            "#BSUB -e logs/%J.err",
        ]
        if gpu:
            directives.append(f'#BSUB -gpu "{gpu_requirement}"')
        directives.extend([
            "",
            "set -Eeuo pipefail",
            f"cd {shlex.quote(remote_dir)}",
            "mkdir -p output work logs",
            f"export BDA_JOB_ID={shlex.quote(job.job_id)}",
            "export BDA_INPUT_MANIFEST=\"$PWD/input/manifest.json\"",
            "export BDA_OUTPUT_DIR=\"$PWD/output\"",
            "export BDA_WORK_DIR=\"$PWD/work\"",
            trusted_command,
        ])
        return "\n".join(directives) + "\n"

    def render_script(self, job: JobSpec) -> str:
        if job.plugin_id == "plugin_rfdiffusion":
            return self._render_rfdiffusion_lsf_script(job)
        if job.plugin_id == "plugin_proteinmpnn":
            return self._render_proteinmpnn_lsf_script(job)
        if job.plugin_id == "plugin_alphafold2":
            return self._render_alphafold2_lsf_script(job)
        trusted_command = self._plugin_commands.get(job.plugin_id)
        if not trusted_command:
            raise RuntimeError(f"remote_lsf_plugin_not_configured:{job.plugin_id}")
        return self._render_lsf_script(job, trusted_command)

    def _upload_workspace(self, job: JobSpec, script: str) -> None:
        if not job.input_dir or not job.work_dir:
            raise RuntimeError("remote_lsf_workspace_missing")
        remote_dir = self._remote_job_dir(job.job_id)
        self._run_ssh(
            f"umask 077 && mkdir -p {shlex.quote(remote_dir)}/input "
            f"{shlex.quote(remote_dir)}/output {shlex.quote(remote_dir)}/work "
            f"{shlex.quote(remote_dir)}/logs"
        )
        script_path = Path(job.work_dir) / "submit.lsf"
        script_path.write_text(script, encoding="utf-8")
        archive = subprocess.run(
            ["tar", "-C", str(Path(job.input_dir).parent), "-cf", "-", "input", "work/submit.lsf"],
            capture_output=True,
            check=True,
        ).stdout
        encoded_archive = base64.b64encode(archive)
        self._run_ssh(
            f"base64 -d | tar -C {shlex.quote(remote_dir)} -xf -",
            input_data=encoded_archive,
            timeout=120,
        )

    def _download_outputs(self, job_id: str, output_dir: str) -> None:
        remote_dir = self._remote_job_dir(job_id)
        result = self._run_ssh(
            f"test -d {shlex.quote(remote_dir)}/output && "
            f"tar -C {shlex.quote(remote_dir)}/output -cf - . | base64",
            timeout=120,
            check=False,
        )
        if result.returncode != 0 or not result.stdout:
            return
        encoded = b"".join(result.stdout.split())
        try:
            archive = base64.b64decode(encoded, validate=False)
        except Exception:
            return
        local_output = Path(output_dir)
        local_output.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["tar", "-C", str(local_output), "-xf", "-"],
            input=archive,
            capture_output=True,
            check=True,
        )

    def submit(self, job: JobSpec) -> JobHandle:
        script = self.render_script(job)
        self._upload_workspace(job, script)
        remote_dir = self._remote_job_dir(job.job_id)
        result = self._run_ssh(
            f"cd {shlex.quote(remote_dir)} && bsub < work/submit.lsf",
            timeout=30,
        )
        output = result.stdout.decode("utf-8", errors="replace")
        match = re.search(r"Job <(\d+)>", output)
        if not match:
            raise RuntimeError(f"remote_lsf_submit_unrecognized:{output.strip()}")
        return JobHandle(job_id=job.job_id, external_id=match.group(1))

    def status(self, job_id: str, external_id: str | None = None) -> JobStatus:
        if not external_id:
            return JobStatus(job_id=job_id, status="not_found")
        result = self._run_ssh(
            f"bjobs -noheader -o stat {shlex.quote(external_id)}",
            check=False,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            if "Permission denied" in stderr or "ssh" in stderr.lower():
                raise RuntimeError(self._ssh_error_summary(stderr))
        raw = result.stdout.decode("utf-8", errors="replace").strip().split()
        lsf_status = raw[0] if raw else ""
        status = self._LSF_STATUS.get(lsf_status)
        if status is None:
            history = self._run_ssh(
                f"bhist -n 1 -noheader -o stat {shlex.quote(external_id)}",
                check=False,
            )
            if history.returncode != 0:
                stderr = history.stderr.decode("utf-8", errors="replace").strip()
                if "Permission denied" in stderr or "ssh" in stderr.lower():
                    raise RuntimeError(self._ssh_error_summary(stderr))
            history_raw = history.stdout.decode("utf-8", errors="replace").strip().split()
            status = self._LSF_STATUS.get(history_raw[0] if history_raw else "", "not_found")
        logs = self.logs(job_id, external_id, tail=200)
        return JobStatus(job_id=job_id, status=status, logs=logs)

    def cancel(self, job_id: str, external_id: str | None = None) -> bool:
        if not external_id:
            return False
        return self._run_ssh(f"bkill {shlex.quote(external_id)}", check=False).returncode == 0

    def logs(self, job_id: str, external_id: str | None = None, tail: int = 100) -> str:
        if not external_id:
            return ""
        remote_dir = self._remote_job_dir(job_id)
        safe_tail = min(max(int(tail), 1), 2000)
        result = self._run_ssh(
            f"cd {shlex.quote(remote_dir)} && "
            f"tail -n {safe_tail} "
            f"{shlex.quote(external_id)}.out {shlex.quote(external_id)}.err "
            f"logs/{shlex.quote(external_id)}.log "
            f"logs/{shlex.quote(external_id)}.out logs/{shlex.quote(external_id)}.err "
            "2>/dev/null",
            check=False,
        )
        return result.stdout.decode("utf-8", errors="replace")

    def collect_outputs(self, job_id: str, output_dir: str) -> None:
        self._download_outputs(job_id, output_dir)

    def health(self) -> dict[str, object]:
        queues = " ".join(
            shlex.quote(queue)
            for queue in dict.fromkeys([self._gpu_queue, self._cpu_queue])
            if queue
        )
        queue_filter = f" {queues}" if queues else ""
        result = self._run_ssh(
            "command -v bsub >/dev/null && command -v bjobs >/dev/null && "
            "printf 'BDA_LSF_OK\\n' && "
            f"bqueues -noheader -o 'queue_name status njobs pend run' {queue_filter} 2>/dev/null && "
            "printf 'BDA_LSF_ALL_QUEUES\\n' && "
            "bqueues -noheader -o 'queue_name status njobs pend run' 2>/dev/null",
            timeout=60,
            check=False,
        )
        text = result.stdout.decode("utf-8", errors="replace")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        connected = result.returncode == 0 and "BDA_LSF_OK" in lines
        ok_marker = lines.index("BDA_LSF_OK") if "BDA_LSF_OK" in lines else -1
        all_marker = lines.index("BDA_LSF_ALL_QUEUES") if "BDA_LSF_ALL_QUEUES" in lines else len(lines)
        return {
            "mode": "remote_lsf",
            "connected": connected,
            "host": self._host,
            "remote_root": self._remote_root,
            "queues": lines[ok_marker + 1:all_marker] if connected else [],
            "all_queues": lines[all_marker + 1:] if connected and all_marker < len(lines) else [],
            "reason": None if connected else (result.stderr + result.stdout).decode("utf-8", errors="replace").strip(),
        }


_adapter_cache: dict[str, ComputeAdapter] = {}


def get_compute_adapter() -> ComputeAdapter:
    """Return a cached compute adapter for the configured mode.

    Adapters (notably ``LocalDockerAdapter``, which opens a Docker client) are
    expensive to construct, so we memoize one instance per compute mode instead
    of building a fresh adapter on every call.
    """
    from ..settings import get_settings

    mode = get_settings().bda_compute_mode
    cached = _adapter_cache.get(mode)
    if cached is not None:
        return cached

    if mode == "docker":
        adapter: ComputeAdapter = LocalDockerAdapter()
    elif mode == "local":
        adapter = LocalProcessAdapter()
    elif mode == "remote_lsf":
        adapter = RemoteLsfAdapter()
    else:
        adapter = DemoComputeAdapter()
    _adapter_cache[mode] = adapter
    return adapter


def reset_compute_adapter_cache() -> None:
    """Clear the cached adapters (useful in tests or after a settings change)."""
    _adapter_cache.clear()
