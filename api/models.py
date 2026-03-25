from pydantic import BaseModel


class MatchRef(BaseModel):
    uri: str
    label: str
    source: str | None = None


class Definition(BaseModel):
    text: str
    source: str | None = None


class ConceptSummary(BaseModel):
    uri: str
    label: str
    alt_label: str | None = None
    type: str | None = None
    definitions: list[Definition] = []


class ConceptDetail(ConceptSummary):
    exact_match: list[MatchRef] = []
    close_match: list[MatchRef] = []
    broader: list[ConceptSummary] = []
    narrower: list[ConceptSummary] = []
    procedures: list[ConceptSummary] = []


class SearchResult(BaseModel):
    query: str
    total: int
    results: list[ConceptSummary]


