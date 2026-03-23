from __future__ import annotations

from lcars.core.versioning import load_release_version


def test_release_version_is_static() -> None:
    release = load_release_version()

    assert release.version == "1.0.0"
    assert release.stardate == "2026.082.1"
    assert release.released_at == "2026-03-23T00:00:00Z"
