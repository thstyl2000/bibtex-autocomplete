"""Lookup info from https://zbmath.org"""

from typing import Dict, Iterable, Iterator, List, Optional

from ..bibtex.author import Author
from ..bibtex.constants import FieldNames
from ..bibtex.entry import BibtexEntry
from ..bibtex.normalize import author_search_key, normalize_doi
from ..lookups.lookups import JSON_Lookup
from ..utils.constants import QUERY_MAX_RESULTS
from ..utils.safe_json import JSONType, SafeJSON



class ZbMathLookup(JSON_Lookup):
    """Lookup for info on https://zbmath.org
    Uses the zbMATH Open API documented here:
    https://api.zbmath.org/

    example URLs:
    DOI mode:
    https://api.zbmath.org/v1/document/_search?search_string=doi:10.1007/3-540-46425-5_21&format=json
    Title + author:
    https://api.zbmath.org/v1/document/_search?search_string=Lamiraux&format=json
    """

    name = "zbmath"

    # ============= Performing Queries =====================

    domain = "api.zbmath.org"
    path = "/v1/document/_search"

    # zbMATH requires agreement to their terms via a cookie
    headers = {"Cookie": "tsnc=agreed"}

    def iter_queries(self) -> Iterator[None]:
        """Perform DOI, title+author and title searches without normalizing"""
        self.title = self.entry.title.to_str()
        self.doi = self.entry.doi.to_str()
        authors = self.entry.author.value
        if authors is not None:
            self.authors = [author_search_key(author) for author in authors]

        if self.query_doi and self.doi is not None:
            yield None
            self.doi = None

        if self.title is None:
            return

        if self.query_author_title and self.authors is not None:
            yield None
            self.authors = None

        if self.query_title:
            yield None


    def get_params(self) -> Dict[str, str]:
        params: Dict[str, str] = {
            "format": "json",
            "results_per_page": str(QUERY_MAX_RESULTS),
        }
        if self.doi is not None:
            params["search_string"] = f"doi:{self.doi}"
            return params
        if self.title is None:
            raise ValueError("zbMATH called with no title")

        # Quote the title to mimic the website's exact phrase search behaviour
        search = f'"{self.title}"'
        if self.authors:
            search += " " + " ".join(self.authors)
        params["search_string"] = search
        return params

    # ============= Parsing results into entries =====================

    def get_results(self, data: bytes) -> Optional[Iterable[SafeJSON]]:
        """Return the result list and track the count"""
        json = SafeJSON.from_bytes(data)
        results = list(json["result"].iter_list())
        self._result_count = len(results)
        return results


    @staticmethod
    def get_authors(authors: SafeJSON) -> List[Author]:
        """Return a bibtex formatted list of authors"""
        formatted: List[Author] = []
        for author in authors.iter_list():
            name = author["name"].to_str()
            if name is None:
                continue
            aut = Author.from_name(name)
            if aut is not None:
                formatted.append(aut)
        return formatted

    def get_value(self, result: SafeJSON) -> BibtexEntry:
        """Extract bibtex data from JSON output"""
        values = BibtexEntry(self.name, self.entry.id)
        values.author.set(self.get_authors(result["contributors"]["authors"]))

        doi = normalize_doi(result["doi"].to_str())
        if doi is None:
            for link in result["links"].iter_list():
                if link["type"].to_str() == "doi":
                    doi = normalize_doi(link["identifier"].to_str())
                    if doi is not None:
                        break
        if doi is None:
            doi = normalize_doi(self.doi)
        values.doi.set(doi)

        source = result["source"]
        doc_type = result["document_type"]["code"].to_str()
        book = next(source["book"].iter_list(), None)
        series = next(source["series"].iter_list(), None)

        if doc_type == "j" and series is not None:
            values.journal.set(series["title"].to_str())
            values.volume.set(series["volume"].to_str())
            values.number.set(series["issue"].to_str())
            for issn in series["issn"].iter_list():
                num = issn["number"].to_str()
                if num is not None:
                    values.issn.set_str(num)
                    break
            values.publisher.set(series["publisher"].to_str())
        else:
            if book is not None:
                values.publisher.set(book["publisher"].to_str())
                for isbn in book["isbn"].iter_list():
                    num = isbn["number"].to_str()
                    if num is not None:
                        values.isbn.set(num)
                        break
            if series is not None:
                values.series.set(series["title"].to_str())
                if values.publisher.to_str() is None:
                    values.publisher.set(series["publisher"].to_str())

        values.pages.set_str(source["pages"].to_str())
        values.title.set(result["title"]["title"].to_str())
        values.url.set(result["zbmath_url"].to_str())
        values.year.set(result["year"].to_str())
        return values

    def get_last_query_info(self) -> Dict[str, JSONType]:
        info = super().get_last_query_info()
        if hasattr(self, "_result_count"):
            info["zbmath-result-count"] = self._result_count
        return info


    # Set of fields we can get from a query.
    # If all are already present on an entry, the query can be skipped.
    fields = {
        FieldNames.AUTHOR,
        FieldNames.ISBN,
        FieldNames.ISSN,
        FieldNames.JOURNAL,
        FieldNames.DOI,
        FieldNames.NUMBER,
        FieldNames.PAGES,
        FieldNames.PUBLISHER,
        FieldNames.SERIES,
        FieldNames.TITLE,
        FieldNames.URL,
        FieldNames.VOLUME,
        FieldNames.YEAR,
    }
