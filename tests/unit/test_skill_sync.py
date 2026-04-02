from __future__ import annotations

import json
from pathlib import Path

import pytest

from rl_developer_memory.skill_bundle_sync import (
    PLUGIN_NAME,
    ensure_marketplace_entry,
    resolve_surface_paths,
    sync_global_skill_surfaces,
)


def test_resolve_surface_paths_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.delenv("AGENTS_HOME", raising=False)

    surfaces = resolve_surface_paths()

    assert surfaces.codex_home == (tmp_path / ".codex").resolve()
    assert surfaces.agents_home == (tmp_path / ".agents").resolve()
    assert surfaces.codex_plugin_root == surfaces.codex_home / "local-plugins" / PLUGIN_NAME
    assert surfaces.agents_plugins_root == surfaces.agents_home / "plugins" / "plugins" / PLUGIN_NAME


def test_ensure_marketplace_entry_idempotent(tmp_path: Path) -> None:
    marketplace_path = tmp_path / "plugins" / "marketplace.json"

    first = ensure_marketplace_entry(marketplace_path)
    second = ensure_marketplace_entry(marketplace_path)

    payload = json.loads(marketplace_path.read_text(encoding="utf-8"))
    names = [item["name"] for item in payload["plugins"]]

    assert first is True
    assert second is False
    assert names.count(PLUGIN_NAME) == 1
    assert payload["plugins"][0]["source"]["path"] == f"./plugins/{PLUGIN_NAME}"


def test_sync_global_skill_surfaces_copy_mode(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    codex_home = tmp_path / ".codex"
    agents_home = tmp_path / ".agents"

    report = sync_global_skill_surfaces(
        repo_root,
        mode="copy",
        codex_home=codex_home,
        agents_home=agents_home,
    )

    codex_target = Path(report.codex_target)
    agents_target = Path(report.agents_target)
    marketplace_path = Path(report.marketplace_json)

    assert (codex_target / ".codex-plugin" / "plugin.json").is_file()
    assert (codex_target / "skills" / "rl-developer-workflow" / "SKILL.md").is_file()
    assert (codex_target / "skills" / "rl-developer-memory-self-learning" / "skill.spec.yaml").is_file()
    assert (agents_target / "docs" / "SKILL_INSTALL_SYNC.md").is_file()
    assert marketplace_path.is_file()

    payload = json.loads(marketplace_path.read_text(encoding="utf-8"))
    assert any(item.get("name") == PLUGIN_NAME for item in payload.get("plugins", []))


def test_sync_global_skill_surfaces_symlink_mode_uses_relative_links(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    codex_home = tmp_path / ".codex"
    agents_home = tmp_path / ".agents"

    report = sync_global_skill_surfaces(
        repo_root,
        mode="symlink",
        codex_home=codex_home,
        agents_home=agents_home,
    )

    codex_target = Path(report.codex_target)
    agents_target = Path(report.agents_target)
    assert codex_target.is_symlink()
    assert agents_target.is_symlink()
    assert not str(codex_target.readlink()).startswith("/")
    assert not str(agents_target.readlink()).startswith("/")
