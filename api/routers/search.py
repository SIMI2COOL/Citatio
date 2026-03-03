"""Search endpoint: run Google Scholar search and return Excel/CSV file."""
import io
import re
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from sortgs import run_search

router = APIRouter(prefix="/api", tags=["search"])

MAX_CSV_FNAME = 255


class SearchRequest(BaseModel):
    """Request body for POST /api/search."""

    keyword: str = Field(..., min_length=1, description="Search keyword(s)")
    exact_phrase: bool = Field(False, description="Wrap keyword in quotes for exact phrase")
    sortby: str = Field("Citations", description="Sort by 'Citations' or 'cit/year'")
    start_year: Optional[int] = Field(None, ge=1900, le=2100)
    end_year: Optional[int] = Field(None, ge=1900, le=2100)
    langfilter: Optional[List[str]] = Field(None, description="Language codes e.g. pt, es, fr, de")
    nresults: int = Field(100, ge=10, le=200, description="Number of results (max 200)")
    format: str = Field("xlsx", description="Response format: xlsx or csv")


def _sanitize_filename(s: str) -> str:
    """Make a safe filename from keyword."""
    name = re.sub(r"[\s:]+", "_", s)[:MAX_CSV_FNAME]
    return name or "scholar_results"


@router.post("/search")
def post_search(request: SearchRequest):
    """
    Run a Google Scholar search and return the result file (Excel or CSV).
    """
    keyword = request.keyword.strip()
    if request.exact_phrase:
        keyword = f"'{keyword}'"

    sortby = request.sortby if request.sortby in ("Citations", "cit/year") else "Citations"
    langfilter = request.langfilter if request.langfilter else "All"

    try:
        df = run_search(
            keyword=keyword,
            nresults=request.nresults,
            sortby=sortby,
            start_year=request.start_year,
            end_year=request.end_year,
            langfilter=langfilter,
            debug=False,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Search failed: {str(e)}") from e

    base_name = _sanitize_filename(keyword.replace("'", ""))

    if request.format == "csv":
        buffer = io.StringIO()
        df.to_csv(buffer, encoding="utf-8", index=True)
        buffer.seek(0)
        return StreamingResponse(
            iter([buffer.getvalue().encode("utf-8")]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{base_name}.csv"'
            },
        )

    # xlsx
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Results", index=True)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{base_name}.xlsx"'
        },
    )
