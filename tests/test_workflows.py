"""
Unit tests for workflow definition files (.md with YAML frontmatter).

Each workflow file in workflows/ is tested individually via parametrized
fixtures defined in conftest.py.

Test categories
---------------
1. Frontmatter structure  – YAML is parseable; required fields exist.
2. Field value validation – ``permissions`` and ``timeout-minutes`` values.
3. safe-outputs structure – when present the value must be a mapping.
4. Markdown body          – each top-level workflow has a markdown heading.
5. Docs correspondence    – every top-level workflow has a matching docs/ file.

Implementation notes
--------------------
* YAML 1.1 (PyYAML default) treats the bare keyword ``on`` as boolean True.
  All checks for the ``on`` trigger field use ``conftest.HAS_ON_KEY`` which
  tests for both ``True`` and ``"on"`` as dict keys.
* Some shared fragments (e.g. ``shared/reporting.md``) contain no YAML
  frontmatter at all – they are pure Markdown.  Those files are explicitly
  skipped where frontmatter presence is a pre-condition.
"""

import re

import pytest
import yaml

from conftest import (
    DOCS_DIR,
    HAS_ON_KEY,
    TOP_LEVEL_WORKFLOW_FILES,
    WORKFLOWS_DIR,
    WorkflowFile,
)


# ---------------------------------------------------------------------------
# 1. Frontmatter structure
# ---------------------------------------------------------------------------


class TestFrontmatterParseable:
    """Every top-level workflow file must have valid, parseable YAML frontmatter."""

    def test_frontmatter_present(
        self, top_level_workflow_file: WorkflowFile
    ) -> None:
        """Top-level workflow files must begin with a ``---`` frontmatter block."""
        assert top_level_workflow_file.has_frontmatter, (
            f"{top_level_workflow_file.rel_path}: no YAML frontmatter found. "
            "Top-level workflow files must start with a --- delimited YAML block."
        )

    def test_frontmatter_parses_without_error(
        self, any_workflow_file: WorkflowFile
    ) -> None:
        """Any frontmatter that is present must be valid YAML (no parse errors)."""
        if not any_workflow_file.has_frontmatter:
            pytest.skip("file has no frontmatter block")
        try:
            yaml.safe_load(any_workflow_file.raw_frontmatter)
        except yaml.YAMLError as exc:
            pytest.fail(
                f"{any_workflow_file.rel_path}: YAML frontmatter failed to parse: {exc}"
            )

    def test_frontmatter_is_mapping(self, any_workflow_file: WorkflowFile) -> None:
        """When frontmatter is present, it must parse to a YAML mapping (dict)."""
        if not any_workflow_file.has_frontmatter:
            pytest.skip("file has no frontmatter block")
        assert isinstance(any_workflow_file.frontmatter, dict), (
            f"{any_workflow_file.rel_path}: frontmatter parsed as "
            f"{type(any_workflow_file.frontmatter).__name__}, expected a mapping."
        )


# ---------------------------------------------------------------------------
# 2. Required fields – top-level workflows only
# ---------------------------------------------------------------------------


class TestRequiredFields:
    """Top-level (non-shared) workflow files must contain mandatory fields."""

    def test_on_field_present(self, top_level_workflow_file: WorkflowFile) -> None:
        """The ``on`` trigger field must be present in every top-level workflow.

        Note: PyYAML (YAML 1.1) converts the bare keyword ``on`` to boolean
        ``True``, so both forms are accepted.
        """
        assert HAS_ON_KEY(top_level_workflow_file.frontmatter), (
            f"{top_level_workflow_file.rel_path}: required trigger field 'on' "
            "is missing from the frontmatter."
        )

    def test_permissions_field_present(
        self, top_level_workflow_file: WorkflowFile
    ) -> None:
        """The ``permissions`` field must be present in every top-level workflow."""
        assert "permissions" in top_level_workflow_file.frontmatter, (
            f"{top_level_workflow_file.rel_path}: required field 'permissions' is missing."
        )


# ---------------------------------------------------------------------------
# 3. Field value validation
# ---------------------------------------------------------------------------


class TestPermissionsValue:
    """Validate the value of the ``permissions`` field when present."""

    def test_permissions_is_valid(
        self, top_level_workflow_file: WorkflowFile
    ) -> None:
        """
        ``permissions`` must be either the string ``'read-all'`` or a dict
        mapping permission names to access levels.
        """
        perms = top_level_workflow_file.frontmatter.get("permissions")
        if perms is None:
            pytest.skip("permissions field not present")

        assert perms == "read-all" or isinstance(perms, dict), (
            f"{top_level_workflow_file.rel_path}: 'permissions' must be "
            f"'read-all' or a mapping of permission names to levels, "
            f"got {type(perms).__name__!r}: {perms!r}."
        )

    def test_permissions_dict_values_are_strings(
        self, top_level_workflow_file: WorkflowFile
    ) -> None:
        """When ``permissions`` is a mapping, every value must be a string."""
        perms = top_level_workflow_file.frontmatter.get("permissions")
        if not isinstance(perms, dict):
            pytest.skip("permissions is not a dict")

        for key, value in perms.items():
            assert isinstance(value, str), (
                f"{top_level_workflow_file.rel_path}: permissions['{key}'] "
                f"has non-string value {value!r}."
            )


class TestTimeoutMinutesValue:
    """Validate ``timeout-minutes`` when the field is present."""

    def test_timeout_minutes_is_positive_integer(
        self, any_workflow_file: WorkflowFile
    ) -> None:
        """When ``timeout-minutes`` is present it must be a positive integer."""
        timeout = any_workflow_file.frontmatter.get("timeout-minutes")
        if timeout is None:
            pytest.skip("timeout-minutes not present in this file")

        assert isinstance(timeout, int), (
            f"{any_workflow_file.rel_path}: 'timeout-minutes' must be an integer, "
            f"got {type(timeout).__name__!r}: {timeout!r}."
        )
        assert timeout > 0, (
            f"{any_workflow_file.rel_path}: 'timeout-minutes' must be positive, "
            f"got {timeout}."
        )


# ---------------------------------------------------------------------------
# 4. safe-outputs structure
# ---------------------------------------------------------------------------


class TestSafeOutputs:
    """When ``safe-outputs`` is present it must be a mapping."""

    def test_safe_outputs_is_dict(self, any_workflow_file: WorkflowFile) -> None:
        """``safe-outputs`` must be a YAML mapping when present."""
        safe_outputs = any_workflow_file.frontmatter.get("safe-outputs")
        if safe_outputs is None:
            pytest.skip("safe-outputs not present in this file")

        assert isinstance(safe_outputs, dict), (
            f"{any_workflow_file.rel_path}: 'safe-outputs' must be a mapping "
            f"(dict), got {type(safe_outputs).__name__!r}: {safe_outputs!r}."
        )


# ---------------------------------------------------------------------------
# 5. Markdown body – heading check (top-level only)
# ---------------------------------------------------------------------------

# Match any ATX heading (# through ######) with at least one non-space character.
_HEADING_RE = re.compile(r"^#{1,6}\s+\S", re.MULTILINE)


class TestMarkdownBody:
    """Top-level workflow files must have at least one Markdown heading in the body."""

    def test_body_has_heading(self, top_level_workflow_file: WorkflowFile) -> None:
        """The body (after the frontmatter) must contain at least one ATX heading."""
        body = top_level_workflow_file.body
        assert _HEADING_RE.search(body), (
            f"{top_level_workflow_file.rel_path}: no Markdown heading (## ...) "
            "found in the workflow body. Each workflow file should have a title "
            "or section heading."
        )


# ---------------------------------------------------------------------------
# 6. Docs / workflows correspondence
# ---------------------------------------------------------------------------


class TestDocsCorrespondence:
    """Every top-level workflow must have a matching file in docs/."""

    def test_docs_file_exists(
        self, top_level_workflow_file: WorkflowFile
    ) -> None:
        """
        For ``workflows/foo.md`` there must be a corresponding ``docs/foo.md``.
        Shared fragments (in workflows/shared/) are excluded from this check.
        """
        workflow_filename = top_level_workflow_file.path.name
        expected_doc = DOCS_DIR / workflow_filename
        assert expected_doc.exists(), (
            f"{top_level_workflow_file.rel_path}: no matching docs file found at "
            f"docs/{workflow_filename}. Every top-level workflow should have a "
            "corresponding documentation file."
        )
