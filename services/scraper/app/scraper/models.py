"""Dataclasses for the in-flight scrape pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DocumentInfo:
    """One document inside an airport's DFS chapter page."""

    dfs_name: str
    normalized_name: str
    page_hash: str
    page_url: str
    permalink: str = ""
    my_url: str = ""
    chart_type: str = "other"
    chart_suffix: str | None = None
    preview_file: str | None = None
    print_file: str | None = None
    error: str | None = None


@dataclass
class AirportInfo:
    """An airport entry discovered from the DFS letter index."""

    name: str
    icao: str
    index_text: str
    chapter_hash: str
    documents: list[DocumentInfo] = field(default_factory=list)
