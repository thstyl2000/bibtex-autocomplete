from typing import Dict

import pytest

from bibtexautocomplete.APIs.zbmath import ZbMathLookup
from bibtexautocomplete.bibtex.author import Author
from bibtexautocomplete.bibtex.entry import BibtexEntry
from bibtexautocomplete.utils.safe_json import SafeJSON


def test_get_authors() -> None:
    authors = SafeJSON.from_str('[{"name":"Lamiraux, F."}, {"name":"Laumond, J.-P."}]')
    assert ZbMathLookup.get_authors(authors) == [
        Author("Lamiraux", "F."),
        Author("Laumond", "J.-P."),
    ]


entries = [
    (
        {
            "title": "Nonlocal models for nonlinear, dispersive waves",
            "author": "Abdelouhab, L. and Bona, J.L. and Felland, M. and Saut, J.-C.",
            "ID": "AbdelouhabBonaFellandSaut89",
        },
        "10.1016/0167-2789(89)90050-x",
    ),
    (
        {
            "title": "Pseudodifferential and singular integral operators",
            "author": "Abels, H.",
            "ID": "Abels2012",
        },
        "Pseudodifferential and singular integral operators",
    ),
    (
        {
            "doi": "10.1002/sapm1983692135",
            "ID": "AblowitzBaryaacovFokas83",
        },
        "10.1002/sapm1983692135",
    ),
    (
        {
            "title": "Solitons, Nonlinear Evolution Equations and Inverse Scattering",
            "author": "Ablowitz, M. A. and Clarkson, P. A.",
            "doi": "10.1017/cbo9780511623998",
            "ID": "AblowitzClarkson",
        },
        "10.1017/cbo9780511623998",
    ),
]


@pytest.mark.parametrize(("entry", "expected"), entries)
def test_zbmath_lookup(entry: Dict[str, str], expected: str) -> None:
    bib = BibtexEntry.from_entry("test", entry)
    lookup = ZbMathLookup(bib)
    res = lookup.query()
    if res is None:
        status = lookup.get_last_query_info().get("response-status")
        if isinstance(status, int):
            assert status == 429 or status >= 500
    else:
        if entry.get("doi"):
            assert res.doi.to_str() == expected
        else:
            title = res.title.to_str()
            assert title is not None and expected.lower() in title.lower()


def test_zbmath_lookup_no_title() -> None:
    entry = {
        "author": "ABLOWITZ, M. J. and FOKAS, A. S. and MUSSLIMANI, Z. H.",
        "ID": "AblowitzFokasMusslimani06",
    }
    bib = BibtexEntry.from_entry("test", entry)
    lookup = ZbMathLookup(bib)
    assert lookup.query() is None
