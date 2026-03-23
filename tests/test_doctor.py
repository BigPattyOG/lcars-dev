from __future__ import annotations

from lcars.core.paths import LcarsPaths
from lcars.systems.doctor import run_diagnostics


def test_doctor_reports_missing_token(runtime_env) -> None:
    checks = run_diagnostics(paths=LcarsPaths.discover())
    by_name = {check.name: check for check in checks}

    assert by_name["Environment File"].status == "WARN"
    assert by_name["Discord Token"].status == "FAIL"
    assert by_name["Dependency:click"].status == "OK"
