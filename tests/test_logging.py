from types import SimpleNamespace

from bibtexautocomplete.bibtex.entry import BibtexEntry
from bibtexautocomplete.core.autocomplete import BibtexAutocomplete


class ThreadStub:
    def __init__(self, name, result, info):
        self.lookup = SimpleNamespace(name=name)
        self.result = [(result, info)]


def test_log_not_found(caplog, tmp_path):
    not_found_log = tmp_path / "not-found.log"
    multi_hits_log = tmp_path / "multi-hits.log"
    btac = BibtexAutocomplete(
        lookups=[],
        verbose=0,
        not_found_log_path=not_found_log,
        multiple_hits_log_path=multi_hits_log,
    )
    entry = {"ID": "missing"}
    thread = ThreadStub("stub", None, {"hit-count": 0})
    btac.update_entry(entry, set(), [thread])
    assert "No matches found for 'missing'" in caplog.text
    assert not_found_log.read_text(encoding="utf-8").strip().splitlines() == ["missing"]
    assert multi_hits_log.read_text(encoding="utf-8") == ""


def test_log_multiple_hits(caplog, tmp_path):
    not_found_log = tmp_path / "not-found.log"
    multi_hits_log = tmp_path / "multi-hits.log"
    btac = BibtexAutocomplete(
        lookups=[],
        verbose=0,
        not_found_log_path=not_found_log,
        multiple_hits_log_path=multi_hits_log,
    )
    entry = {"ID": "dup"}
    res = BibtexEntry("src", "dup")
    thread = ThreadStub("stublookup", res, {"hit-count": 3})
    btac.update_entry(entry, set(), [thread])
    assert "Entry 'dup' matched multiple results: stublookup (3 hits)" in caplog.text
    assert not_found_log.read_text(encoding="utf-8") == ""
    assert (
        multi_hits_log.read_text(encoding="utf-8").strip().splitlines()
        == ["dup: stublookup (3 hits)"]
    )
