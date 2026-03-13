"""
Pytest configuration and shared fixtures for workflow validation tests.
"""

import os
import re
from pathlib import Path
from typing import NamedTuple

import pytest
import yaml

# Repository root and key directories
REPO_ROOT = Path(__file__).parent.parent
WORKFLOWS_DIR = REPO_ROOT / "workflows"
DOCS_DIR = REPO_ROOT / "docs"

# YAML 1.1 (PyYAML default) treats the bare keyword ``on`` as boolean True.
# All checks for the ``on`` trigger field use ``has_on_key`` which tests for
# both ``True`` and ``"on"`` as dict keys.
def has_on_key(fm: dict) -> bool:
    """Return True when *fm* contains an ``on`` trigger field.

    PyYAML (YAML 1.1) converts the bare keyword ``on`` to the Python bool
    ``True``, so both ``True`` and the string ``"on"`` are checked.
    """
    return True in fm or "on" in fm


class WorkflowFile(NamedTuple):
    """Parsed representation of a workflow markdown file."""

    path: Path
    """Absolute path to the file."""

    rel_path: str
    """Path relative to the workflows/ directory (e.g. 'issue-triage.md')."""

    frontmatter: dict
    """Parsed YAML frontmatter (empty dict if file has no frontmatter)."""

    body: str
    """Markdown body content that follows the frontmatter delimiters."""

    raw_frontmatter: str
    """Raw YAML text between the ``---`` delimiters (empty string if none)."""

    has_frontmatter: bool
    """True when the file begins with a ``---`` frontmatter block."""


# ---------------------------------------------------------------------------
# Helper – parse a single workflow file
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(
    r"\A---\r?\n(.*?)\r?\n---\r?\n(.*)",
    re.DOTALL,
)


def _parse_workflow_file(path: Path) -> WorkflowFile:
    """Parse *path* and return a :class:`WorkflowFile`."""
    content = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(content)
    if match:
        raw_fm = match.group(1)
        body = match.group(2)
        try:
            frontmatter = yaml.safe_load(raw_fm) or {}
        except yaml.YAMLError:
            frontmatter = {}  # parsing errors are tested separately
        has_frontmatter = True
    else:
        raw_fm = ""
        body = content
        frontmatter = {}
        has_frontmatter = False

    rel_path = str(path.relative_to(WORKFLOWS_DIR))
    return WorkflowFile(
        path=path,
        rel_path=rel_path,
        frontmatter=frontmatter,
        body=body,
        raw_frontmatter=raw_fm,
        has_frontmatter=has_frontmatter,
    )


# ---------------------------------------------------------------------------
# Collect files
# ---------------------------------------------------------------------------

def _collect_workflow_files() -> list[WorkflowFile]:
    """Return all .md files under workflows/ as WorkflowFile objects."""
    return [
        _parse_workflow_file(p)
        for p in sorted(WORKFLOWS_DIR.rglob("*.md"))
    ]


def _is_shared(wf: WorkflowFile) -> bool:
    """Return True if the file lives inside workflows/shared/."""
    return wf.rel_path.startswith("shared" + os.sep) or wf.rel_path.startswith(
        "shared/"
    )


# ---------------------------------------------------------------------------
# Module-level cached collections (built once per test session)
# ---------------------------------------------------------------------------

ALL_WORKFLOW_FILES: list[WorkflowFile] = _collect_workflow_files()
TOP_LEVEL_WORKFLOW_FILES: list[WorkflowFile] = [
    wf for wf in ALL_WORKFLOW_FILES if not _is_shared(wf)
]
SHARED_WORKFLOW_FILES: list[WorkflowFile] = [
    wf for wf in ALL_WORKFLOW_FILES if _is_shared(wf)
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _wf_id(wf: WorkflowFile) -> str:
    """Pytest ID for a WorkflowFile – uses the relative path."""
    return wf.rel_path


@pytest.fixture(
    params=ALL_WORKFLOW_FILES,
    ids=[_wf_id(wf) for wf in ALL_WORKFLOW_FILES],
)
def any_workflow_file(request: pytest.FixtureRequest) -> WorkflowFile:
    """Parametrized fixture yielding every workflow file (including shared/)."""
    return request.param


@pytest.fixture(
    params=TOP_LEVEL_WORKFLOW_FILES,
    ids=[_wf_id(wf) for wf in TOP_LEVEL_WORKFLOW_FILES],
)
def top_level_workflow_file(request: pytest.FixtureRequest) -> WorkflowFile:
    """Parametrized fixture yielding only top-level (non-shared) workflow files."""
    return request.param


@pytest.fixture(
    params=SHARED_WORKFLOW_FILES,
    ids=[_wf_id(wf) for wf in SHARED_WORKFLOW_FILES],
)
def shared_workflow_file(request: pytest.FixtureRequest) -> WorkflowFile:
    """Parametrized fixture yielding only shared/ fragment files."""
    return request.param
