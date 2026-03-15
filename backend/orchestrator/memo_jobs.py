from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any, Awaitable, Callable
from uuid import uuid4

from orchestrator.railtracks_flow import assess_flow

AssessRunner = Callable[[dict[str, Any]], Awaitable[Any]]


class QueueFullError(RuntimeError):
    pass


class MemoJobManager:
    def __init__(
        self,
        *,
        queue_maxsize: int,
        worker_count: int,
        timeout_seconds: float,
        runner: AssessRunner = assess_flow,
    ) -> None:
        self._queue_maxsize = max(1, int(queue_maxsize))
        self._queue: asyncio.Queue[str | None] | None = None
        self._worker_count = max(1, int(worker_count))
        self._timeout_seconds = max(1.0, float(timeout_seconds))
        self._runner: AssessRunner = runner
        self._workers: list[asyncio.Task[None]] = []
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock: asyncio.Lock | None = None

    async def _ensure_runtime(self) -> None:
        if self._queue is None:
            self._queue = asyncio.Queue(maxsize=self._queue_maxsize)
        if self._lock is None:
            self._lock = asyncio.Lock()

    async def start(self) -> None:
        await self._ensure_runtime()
        if self._workers:
            return
        for worker_index in range(self._worker_count):
            self._workers.append(asyncio.create_task(self._worker_loop(worker_index)))

    async def stop(self) -> None:
        if not self._workers:
            return
        assert self._queue is not None
        for _ in self._workers:
            await self._queue.put(None)
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        # Recreate async primitives on next start to avoid event-loop affinity issues.
        self._queue = None
        self._lock = None

    async def submit(self, payload: dict[str, Any]) -> str:
        await self.start()
        assert self._queue is not None
        assert self._lock is not None
        if self._queue.full():
            raise QueueFullError("memo_job_queue_full")

        now = datetime.now(UTC)
        job_id = f"memo-job-{uuid4().hex[:12]}"
        async with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "status": "queued",
                "created_at": now,
                "updated_at": now,
                "payload": payload,
                "result": None,
                "error": None,
            }

        await self._queue.put(job_id)
        return job_id

    async def get_status(self, job_id: str) -> dict[str, Any] | None:
        await self._ensure_runtime()
        assert self._lock is not None
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            return {
                "job_id": job["job_id"],
                "status": job["status"],
                "created_at": job["created_at"],
                "updated_at": job["updated_at"],
                "error": job["error"],
                "has_result": job["result"] is not None,
            }

    async def get_result(self, job_id: str) -> dict[str, Any] | None:
        await self._ensure_runtime()
        assert self._lock is not None
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            return {
                "status": job["status"],
                "result": job["result"],
                "error": job["error"],
            }

    async def _worker_loop(self, worker_index: int) -> None:
        while True:
            job_id = await self._queue.get()
            if job_id is None:
                self._queue.task_done()
                break

            await self._update_job(job_id, status="running")
            try:
                payload = await self._get_payload(job_id)
                if payload is None:
                    raise RuntimeError("job_payload_missing")

                assessment = await asyncio.wait_for(self._runner(payload), timeout=self._timeout_seconds)
                result_payload = self._to_result_payload(assessment)
                await self._update_job(job_id, status="succeeded", result=result_payload)
            except asyncio.TimeoutError:
                await self._update_job(job_id, status="failed", error="memo_job_timeout")
            except Exception as exc:
                await self._update_job(job_id, status="failed", error=str(exc))
            finally:
                self._queue.task_done()

    async def _get_payload(self, job_id: str) -> dict[str, Any] | None:
        await self._ensure_runtime()
        assert self._lock is not None
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            return dict(job.get("payload") or {})

    async def _update_job(
        self,
        job_id: str,
        *,
        status: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        await self._ensure_runtime()
        assert self._lock is not None
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job["status"] = status
            job["updated_at"] = datetime.now(UTC)
            if result is not None:
                job["result"] = result
            if error is not None:
                job["error"] = error

    def _to_result_payload(self, assessment: Any) -> dict[str, Any]:
        if hasattr(assessment, "model_dump"):
            data = assessment.model_dump(mode="json")
        elif isinstance(assessment, dict):
            data = assessment
        else:
            raise TypeError("unsupported_assessment_result")

        methodology = data.get("methodology") if isinstance(data, dict) else {}
        if not isinstance(methodology, dict):
            methodology = {}

        return {
            "proposal_id": data.get("proposal_id"),
            "memo": data.get("memo"),
            "report_narrative": data.get("report_narrative"),
            "methodology": methodology,
            "fallback_used": not bool(methodology.get("railtacks_used", False)),
            "assessment": data,
        }
