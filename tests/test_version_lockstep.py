"""Version surfaces must move together.

The portfolio's dominant defect class is one surface bumped while another
(manifest constant / README badge / site key / lockfile) lags. ``VERSION`` is
the single source; everything else is asserted against it.
"""

from __future__ import annotations

import re
from pathlib import Path

import nianbao

ROOT = Path(__file__).resolve().parents[1]


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_version_surfaces_agree():
    version = _read("VERSION").strip()
    assert re.fullmatch(r"\d+\.\d+\.\d+", version), version

    assert nianbao.__version__ == version

    assert re.search(
        rf'^version = "{re.escape(version)}"$', _read("pyproject.toml"), re.MULTILINE
    ), "pyproject.toml version is stale"

    # uv.lock pins the editable project; a manual bump leaves it behind.
    assert re.search(
        rf'^name = "nianbao"\nversion = "{re.escape(version)}"$',
        _read("uv.lock"),
        re.MULTILINE,
    ), "uv.lock still pins another version"

    for readme in ("README.md", "README.en.md"):
        assert f"version-{version}-" in _read(readme), f"{readme} badge is stale"

    assert f'"source_version": "v{version}"' in _read("web/site.json")

    assert f"## v{version}" in _read("CHANGELOG.md"), "CHANGELOG head is stale"
