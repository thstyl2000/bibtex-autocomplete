"""
Lookup info from https://zbmath.org
"""

from typing import Dict, Iterable, List, Optional

from ..bibtex.author import Author
from ..bibtex.constants import FieldNames
from ..bibtex.entry import BibtexEntry
from ..bibtex.normalize import normalize_doi
from ..lookups.lookups import JSON_Lookup
from ..utils.constants import QUERY_MAX_RESULTS
from ..utils.safe_json import SafeJSON


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

    def get_params(self) -> Dict[str, str]:
        params: Dict[str, str] = {"format": "json", "results_per_page": str(QUERY_MAX_RESULTS)}
        if self.doi is not None:
            params["search_string"] = f"doi:{self.doi}"
            return params
        if self.title is None:
            raise ValueError("zbMATH called with no title")
        search = self.title
        if self.authors:
            search += " " + " ".join(self.authors)
        params["search_string"] = search
        return params

    # ============= Parsing results into entries =====================

    def get_results(self, data: bytes) -> Optional[Iterable[SafeJSON]]:
        """Return the result list"""
        json = SafeJSON.from_bytes(data)
        return json["result"].iter_list()

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
        values.doi.set(doi)

        values.pages.set_str(result["source"]["pages"].to_str())
        values.title.set(result["title"]["title"].to_str())
        values.url.set(result["zbmath_url"].to_str())
        values.year.set(result["year"].to_str())
        return values

    # Set of fields we can get from a query.
    # If all are already present on an entry, the query can be skipped.
    fields = {
        FieldNames.AUTHOR,
        FieldNames.DOI,
        FieldNames.PAGES,
        FieldNames.TITLE,
        FieldNames.URL,
        FieldNames.YEAR,
    }
