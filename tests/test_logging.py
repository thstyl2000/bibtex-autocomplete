from types import SimpleNamespace

from bibtexautocomplete.bibtex.entry import BibtexEntry
from bibtexautocomplete.core.autocomplete import BibtexAutocomplete


class ThreadStub:
    def __init__(self, name, result, info):
        self.lookup = SimpleNamespace(name=name)
        self.result = [(result, info)]


def test_log_not_found(caplog):
    btac = BibtexAutocomplete(lookups=[], verbose=0)
    entry = {"ID": "missing"}
    thread = ThreadStub("stub", None, {"hit-count": 0})
    btac.update_entry(entry, set(), [thread])
    assert "No matches found for 'missing'" in caplog.text


def test_log_multiple_hits(caplog):
    btac = BibtexAutocomplete(lookups=[], verbose=0)
    entry = {"ID": "dup"}
    res = BibtexEntry("src", "dup")
    thread = ThreadStub("stublookup", res, {"hit-count": 3})
    btac.update_entry(entry, set(), [thread])
    assert "Entry 'dup' matched multiple results: stublookup (3 hits)" in caplog.text
