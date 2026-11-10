"""Package the offline AVD Containerlab example without deploying it."""

import hashlib
import io
import os
from pathlib import Path
import tarfile
import tempfile

import yaml


def build_bundle(source_dir: Path, image: str) -> Path:
    if not image.strip():
        raise ValueError("Set DRYDOCK_CEOS_IMAGE to an explicit image reference before packaging.")

    topology_path = source_dir / "FABRIC-topology.clab.yml"
    topology = yaml.safe_load(topology_path.read_text())
    topology["topology"]["kinds"]["arista_ceos"]["image"] = image
    files = {
        topology_path.name: yaml.safe_dump(topology, sort_keys=False).encode(),
        "interface_mapping.json": (source_dir / "interface_mapping.json").read_bytes(),
    }
    for node in topology["topology"]["nodes"].values():
        config_path = node["startup-config"]
        files[config_path] = (source_dir / config_path).read_bytes()

    # Normalize metadata so only the bundled content determines the digest.
    with tempfile.TemporaryDirectory(dir=source_dir) as temporary_dir:
        archive_path = Path(temporary_dir) / "bundle.tar"
        with tarfile.open(archive_path, "w", format=tarfile.USTAR_FORMAT) as archive:
            for name, content in sorted(files.items()):
                member = tarfile.TarInfo(name)
                member.size = len(content)
                member.mode = 0o600
                archive.addfile(member, io.BytesIO(content))
        archive_path.chmod(0o600)
        with archive_path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        checksum_path = Path(temporary_dir) / "bundle.tar.sha256"
        checksum_path.write_text(f"{digest}  bundle.tar\n")
        archive_path.replace(source_dir / archive_path.name)
        checksum_path.replace(source_dir / checksum_path.name)
    return source_dir / "bundle.tar"


if __name__ == "__main__":
    source_dir = Path(__file__).resolve().parents[2] / "artifacts/example/containerlab"
    print(build_bundle(source_dir, os.environ.get("DRYDOCK_CEOS_IMAGE", "")))
