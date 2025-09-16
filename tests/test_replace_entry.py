from __future__ import annotations

from pathlib import Path
from typing import Iterator, List

import pytest

from bibtexautocomplete.bibtex.constants import FieldNamesSet, SearchedFields
from bibtexautocomplete.bibtex.entry import BibtexEntry
from bibtexautocomplete.core import apis, parser
from bibtexautocomplete.core.main import ErrorCodes, main
from bibtexautocomplete.lookups.abstract_entry_lookup import AbstractEntryLookup


class FakeZbMathLookup(AbstractEntryLookup):
    """Lookup that always returns ZbMath-flavoured data."""

    name = "zbmath"
    fields = FieldNamesSet

    def query(self) -> BibtexEntry:
        entry = BibtexEntry(self.name, self.entry.id)
        entry.title.set("ZbMath Title")
        entry.journal.set("Zb Journal")
        return entry


class FakeCrossrefLookup(AbstractEntryLookup):
    """Lookup that returns data distinct from ZbMath for prioritisation tests."""

    name = "crossref"
    fields = FieldNamesSet

    def query(self) -> BibtexEntry:
        entry = BibtexEntry(self.name, self.entry.id)
        entry.title.set("Crossref Title")
        entry.note.set("Crossref Note")
        return entry


@pytest.fixture
def fake_lookups() -> Iterator[None]:
    """Temporarily replace configured lookups with deterministic fakes."""

    original_lookups: List[type[AbstractEntryLookup]] = list(apis.LOOKUPS)
    original_lookup_names = list(apis.LOOKUP_NAMES)

    fake_lookups_list: List[type[AbstractEntryLookup]] = [FakeZbMathLookup, FakeCrossrefLookup]
    new_lookup_names = [cls.name for cls in fake_lookups_list]

    apis.LOOKUPS[:] = fake_lookups_list
    apis.LOOKUP_NAMES[:] = new_lookup_names
    parser.LOOKUP_NAMES[:] = new_lookup_names

    try:
        yield
    finally:
        apis.LOOKUPS[:] = original_lookups
        apis.LOOKUP_NAMES[:] = original_lookup_names
        parser.LOOKUP_NAMES[:] = original_lookup_names


def test_replace_entry_prefers_first_lookup(tmp_path: Path, fake_lookups: None) -> None:
    input_path = tmp_path / "input.bib"
    input_path.write_text(
        "@article{replaceKey,\n"
        "  title = {Original Title},\n"
        "  note = {Original Note}\n"
        "}\n",
        encoding="utf-8",
    )
    output_path = tmp_path / "output.bib"

    exit_code = main([
        "-q",
        "zbmath",
        "-q",
        "crossref",
        "-R",
        "-o",
        str(output_path),
        str(input_path),
    ])

    assert exit_code == ErrorCodes.SUCCESS

    contents = output_path.read_text(encoding="utf-8")
    assert "@article{replaceKey" in contents
    assert "ZbMath Title" in contents
    assert "Zb Journal" in contents
    assert "Crossref Title" not in contents
    assert "Crossref Note" not in contents
    assert "Original Note" not in contents


def test_replace_entry_replaces_complete_entries(tmp_path: Path, fake_lookups: None) -> None:
    input_path = tmp_path / "input.bib"
    original_fields = {field: f"Original {field}" for field in SearchedFields}
    entry_body = ",\n".join(
        f"  {field} = {{{value}}}"
        for field, value in sorted(original_fields.items())
    )
    input_path.write_text(
        "@article{replaceKey,\n"
        f"{entry_body}\n"
        "}\n",
        encoding="utf-8",
    )
    output_path = tmp_path / "output.bib"

    exit_code = main([
        "-q",
        "zbmath",
        "-q",
        "crossref",
        "-R",
        "-o",
        str(output_path),
        str(input_path),
    ])

    assert exit_code == ErrorCodes.SUCCESS

    contents = output_path.read_text(encoding="utf-8")
    assert "ZbMath Title" in contents
    assert "Zb Journal" in contents
    assert "Original title" not in contents
    assert "Original journal" not in contents
    assert "Original address" not in contents


def test_replace_entry_requires_only_query(tmp_path: Path, fake_lookups: None) -> None:
    input_path = tmp_path / "input.bib"
    input_path.write_text("@article{replaceKey,}\n", encoding="utf-8")
    output_path = tmp_path / "output.bib"

    exit_code = main(["-R", "-o", str(output_path), str(input_path)])

    assert exit_code == ErrorCodes.CLI_ERROR
    assert not output_path.exists()
