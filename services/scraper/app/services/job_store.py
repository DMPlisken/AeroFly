"""In-memory job tracking for scrape requests.

Scope: one-process-only, lost on restart. Adequate for Phase 1 — DFS
scraping is a slow, infrequent operation (mostly once-per-AIRAC), so the
data-ingestion side will be polling and storing the final result anyway.
If we ever scale this out to multiple replicas, swap to Postgres-backed
storage.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

JobStatus = Literal["queued", "running", "completed", "failed"]


@dataclass
class ScrapeJob:
    id: UUID = field(default_factory=uuid4)
    icao: str = ""
    edition: str = ""
    status: JobStatus = "queued"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    result: dict | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "icao": self.icao,
            "edition": self.edition,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat(),
            "error": self.error,
            "result": self.result,
        }


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[UUID, ScrapeJob] = {}
        self._lock = asyncio.Lock()

    async def create(self, icao: str, edition: str) -> ScrapeJob:
        async with self._lock:
            job = ScrapeJob(icao=icao, edition=edition)
            self._jobs[job.id] = job
            return job

    async def get(self, job_id: UUID) -> ScrapeJob | None:
        async with self._lock:
            return self._jobs.get(job_id)

    async def mark_running(self, job_id: UUID) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = "running"
                job.started_at = datetime.now(timezone.utc)

    async def mark_completed(self, job_id: UUID, result: dict) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = "completed"
                job.completed_at = datetime.now(timezone.utc)
                job.result = result

    async def mark_failed(self, job_id: UUID, error: str) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = "failed"
                job.completed_at = datetime.now(timezone.utc)
                job.error = error


store = JobStore()
