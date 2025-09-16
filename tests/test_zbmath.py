from typing import Dict, List, Optional, Tuple


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


def test_get_params_quotes_title() -> None:
    bib = BibtexEntry("test", "id")
    lookup = ZbMathLookup(bib)
    lookup.title = "some title"
    lookup.authors = ["smith"]
    params = lookup.get_params()
    assert params["search_string"] == '"some title" smith'


def test_get_value_extracts_doi() -> None:
    bib = BibtexEntry("test", "id")
    lookup = ZbMathLookup(bib)
    data = SafeJSON(
        {
            "contributors": {"authors": []},
            "links": [{"type": "doi", "identifier": "10.1234/abc"}],
            "source": {"pages": None},
            "title": {"title": "foo"},
            "zbmath_url": "u",
            "year": "2000",
            "doi": None,
        }
    )
    values = lookup.get_value(data)
    assert values.doi.to_str() == "10.1234/abc"


def test_get_value_falls_back_to_query_doi() -> None:
    bib = BibtexEntry("test", "id")
    lookup = ZbMathLookup(bib)
    lookup.doi = "10.5678/def"
    data = SafeJSON(
        {
            "contributors": {"authors": []},
            "links": [],
            "source": {"pages": None},
            "title": {"title": "foo"},
            "zbmath_url": "u",
            "year": "2000",
            "doi": None,
        }
    )
    values = lookup.get_value(data)
    assert values.doi.to_str() == "10.5678/def"


def _make_series(short: Optional[str], title: Optional[str]) -> Dict[str, object]:
    return {
        "acronym": None,
        "issn": [],
        "issue": None,
        "issue_id": None,
        "parallel_title": None,
        "part": None,
        "publisher": None,
        "series_id": None,
        "short_title": short,
        "title": title,
        "volume": None,
        "year": None,
    }


def _make_result(series: Dict[str, object]) -> SafeJSON:
    return SafeJSON(
        {
            "contributors": {"authors": []},
            "document_type": {"code": "j"},
            "doi": None,
            "links": [],
            "source": {"book": [], "pages": None, "series": [series]},
            "title": {"title": "foo"},
            "zbmath_url": "u",
            "year": "2000",
        }
    )


def test_get_value_prefers_short_title_for_journal() -> None:
    bib = BibtexEntry("test", "id")
    lookup = ZbMathLookup(bib)
    data = _make_result(_make_series("Abbrev.", "Full Title"))
    values = lookup.get_value(data)
    assert values.journal.to_str() == "Abbrev."


def test_get_value_uses_full_title_when_short_missing() -> None:
    bib = BibtexEntry("test", "id")
    lookup = ZbMathLookup(bib)
    data = _make_result(_make_series(None, "Full Title"))
    values = lookup.get_value(data)
    assert values.journal.to_str() == "Full Title"


def test_matches_author_allows_partial_title() -> None:
    a = BibtexEntry.from_entry(
        "test",
        {
            "title": "Pseudodifferential and singular integral operators",
            "author": "H. Abels",
            "ID": "a",
        },
    )
    b = BibtexEntry.from_entry(
        "test",
        {
            "title": "Pseudodifferential and singular integral operators: An introduction with applications",
            "author": "H. Abels",
            "ID": "b",
        },
    )
    assert a.matches(b) > 0


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
    (
        {
            "title": "Bounds on exponential decay of eigenfunctions of Schrödinger operators",
            "author": "Agmon, Shmuel",
            "doi": "10.1007/bfb0080331",
            "ID": "Agmon1985",
        },
        "10.1007/bfb0080331",
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


def _query_or_skip(entry: Dict[str, str]) -> Optional[BibtexEntry]:
    """Run a zbMATH query for entry, tolerating rate limit responses"""
    bib = BibtexEntry.from_entry("test", entry)
    lookup = ZbMathLookup(bib)
    res = lookup.query()
    if res is None:
        status = lookup.get_last_query_info().get("response-status")
        if isinstance(status, int):
            assert status == 429 or status >= 500
        return None
    return res


def zbmath_status(entries: List[Dict[str, str]]) -> Tuple[List[BibtexEntry], List[BibtexEntry]]:
    """Return bib lists for entries not found and with multiple editions"""
    not_found: List[BibtexEntry] = []
    multiple: List[BibtexEntry] = []
    skipped = False
    for entry in entries:
        bib = BibtexEntry.from_entry("test", entry)
        lookup = ZbMathLookup(bib)
        res = lookup.query()
        info = lookup.get_last_query_info()
        status = info.get("response-status")
        if res is None:
            if status is None or (isinstance(status, int) and (status == 429 or status >= 500)):
                skipped = True
                continue
            not_found.append(bib)
        else:
            count = info.get("zbmath-result-count")
            if isinstance(count, int) and count > 1:
                multiple.append(res)
    if skipped:
        pytest.skip("zbMATH rate limited")
    return not_found, multiple



def test_zbmath_book_fields() -> None:
    entry = {
        "title": "Pseudodifferential and singular integral operators",
        "author": "Abels, H.",
        "ID": "Abels2012",
    }
    res = _query_or_skip(entry)
    if res is not None:
        publisher = res.publisher.to_str()
        assert publisher is not None and "de Gruyter" in publisher
        assert res.isbn.to_str() == "978-3110250305"


def test_zbmath_article_fields() -> None:
    entry = {
        "title": "Nonlocal models for nonlinear, dispersive waves",
        "author": "Abdelouhab, L. and Bona, J.L. and Felland, M. and Saut, J.-C.",
        "ID": "AbdelouhabBonaFellandSaut89",
    }
    res = _query_or_skip(entry)
    if res is not None:
        assert res.journal.to_str() == "Physica D"
        assert res.issn.to_str() == "0167-2789"
        assert res.volume.to_str() == "40"
        assert res.number.to_str() == "3"


def test_zbmath_lookup_no_title() -> None:
    entry = {
        "author": "ABLOWITZ, M. J. and FOKAS, A. S. and MUSSLIMANI, Z. H.",
        "ID": "AblowitzFokasMusslimani06",
    }
    bib = BibtexEntry.from_entry("test", entry)
    lookup = ZbMathLookup(bib)
    assert lookup.query() is None


def test_zbmath_status_lists() -> None:
    entries = [
        {
            "title": "Bounds on exponential decay of eigenfunctions of Schrödinger operators",
            "author": "Agmon, Shmuel",
            "ID": "Agmon1985",
        },
        {
            "title": "Infinite Dimensional Analysis",
            "author": "Aliprantis, C. D. and Border, K. C.",
            "ID": "AliprantisBorder2006",
        },
        {
            "author": "ABLOWITZ, M. J. and FOKAS, A. S. and MUSSLIMANI, Z. H.",
            "ID": "AblowitzFokasMusslimani06",
        },
    ]
    not_found, multiple = zbmath_status(entries)
    assert {e.id for e in not_found} == {"AblowitzFokasMusslimani06"}
    assert {e.id for e in multiple} == {"AliprantisBorder2006"}

