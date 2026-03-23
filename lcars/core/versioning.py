"""Static release metadata access."""

import json
from pathlib import Path

from lcars.core.models import ReleaseVersion

VERSION_FILE = Path(__file__).resolve().parents[1] / "version.json"


def load_release_version(version_file: Path | None = None) -> ReleaseVersion:
    target = version_file or VERSION_FILE
    payload = json.loads(target.read_text(encoding="utf-8"))
    return ReleaseVersion(
        version=payload["version"],
        stardate=payload["stardate"],
        released_at=payload["released_at"],
    )


def build_motd(release: ReleaseVersion, system_status: str) -> str:
    return (
        "LCARS COMPUTER INTERFACE\n"
        f"Stardate {release.stardate}\n"
        f"System Status: {system_status}"
    )
