from bibtexautocomplete.APIs.zbmath import ZbMathLookup
from bibtexautocomplete.bibtex.author import Author
from bibtexautocomplete.utils.safe_json import SafeJSON


def test_get_authors() -> None:
    authors = SafeJSON.from_str('[{"name":"Lamiraux, F."}, {"name":"Laumond, J.-P."}]')
    assert ZbMathLookup.get_authors(authors) == [
        Author("Lamiraux", "F."),
        Author("Laumond", "J.-P."),
    ]
