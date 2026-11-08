"""The Claude Code plugin is well formed: frontmatter, agent names used by the commands, versions."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import yaml

import simanything

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugin"


def frontmatter(path: Path) -> dict:
    m = re.match(r"---\n(.*?)\n---\n", path.read_text(encoding="utf-8"), re.S)
    assert m, f"{path}: no YAML frontmatter"
    data = yaml.safe_load(m.group(1))
    assert isinstance(data, dict), f"{path}: frontmatter is not a mapping"
    return data


AGENTS = sorted((PLUGIN / "agents").glob("*.md"))


def test_agents_frontmatter():
    assert AGENTS
    for p in AGENTS:
        fm = frontmatter(p)
        assert fm.get("name") == p.stem, p
        assert isinstance(fm.get("description"), str) and fm["description"].strip(), p
        assert isinstance(fm.get("tools"), str) and fm["tools"].strip(), p


def test_commands_and_skills_frontmatter():
    commands = sorted((PLUGIN / "commands").glob("*.md"))
    assert commands
    for p in commands:
        assert frontmatter(p).get("description"), p
    skills = sorted((PLUGIN / "skills").glob("*/SKILL.md"))
    assert skills
    for p in skills:
        fm = frontmatter(p)
        assert fm.get("name") == p.parent.name and fm.get("description"), p


def test_commands_name_existing_agents():
    names = {p.stem for p in AGENTS}
    used = set()
    for p in (PLUGIN / "commands").glob("*.md"):
        used |= set(re.findall(r"sim-anything:([a-z-]+)", p.read_text(encoding="utf-8")))
    assert used <= names, f"commands name missing agents: {used - names}"
    assert used == names, f"agents no command runs: {names - used}"


def test_versions_agree():
    plugin = json.loads((PLUGIN / ".claude-plugin/plugin.json").read_text())
    market = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    entry = next(p for p in market["plugins"] if p["name"] == plugin["name"])
    assert (ROOT / entry["source"]).resolve() == PLUGIN
    versions = {plugin["version"], market["metadata"]["version"], entry["version"],
                pyproject["project"]["version"], simanything.__version__}
    assert len(versions) == 1, versions
