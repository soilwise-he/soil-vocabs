from fastapi import APIRouter, HTTPException, Query

from api.models import ConceptDetail, SearchResult
from api.vocab import get_concept_detail, get_property_procedures, search_concepts

router = APIRouter()


@router.get("/search", response_model=SearchResult)
def search(
    q: str = Query(..., min_length=1, description="Search term (searches prefLabel, altLabel)"),
    limit: int = Query(20, ge=1, le=100, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    type: str | None = Query(
        None,
        description="Filter by concept type: 'property' or 'procedure'. Omit for all.",
        enum=["property", "procedure"],
    ),
):
    results, total = search_concepts(q, limit=limit, offset=offset, concept_type=type)
    return SearchResult(query=q, total=total, results=results)


@router.get("/{fragment}/procedures", response_model=SearchResult)
def get_procedures(
    fragment: str,
    q: str | None = Query(None, description="Optional search term to filter procedures by label"),
):
    """Get procedures for a property, optionally filtered by search term."""
    procedures = get_property_procedures(fragment, q=q)
    if procedures is None:
        raise HTTPException(status_code=404, detail=f"Property '{fragment}' not found")
    return SearchResult(query=q or "", total=len(procedures), results=procedures)


@router.get("/{fragment}", response_model=ConceptDetail)
def get_concept(fragment: str):
    """Get full concept detail by fragment ID (e.g. `AerationPorosity`)."""
    concept = get_concept_detail(fragment)
    if concept is None:
        raise HTTPException(status_code=404, detail=f"Concept '{fragment}' not found")
    return concept
