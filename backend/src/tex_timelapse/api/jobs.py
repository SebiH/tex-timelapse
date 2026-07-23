"""In-process job registry for asynchronous project renders.

The web server used to run a full render inside the request handler for
GET /api/projects/<name>/run, holding a worker thread for the entire
(minutes-long) compile+encode and giving the client no id, no progress
handle, and no way to cancel. This module backs the replacement job
endpoints: a render runs on a background task, and the client polls
GET /api/jobs/<id> (progress is also pushed over Socket.IO) and can
DELETE /api/jobs/<id> to cancel cooperatively.

Everything here is in-memory and process-local; a single server process is
assumed (as it already is - the ThreadPoolExecutor and Socket.IO server are
too). Jobs are never persisted.
"""
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class JobStatus(str, Enum):
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


@dataclass
class Job:
    id: str
    project_name: str
    output: str
    status: JobStatus = JobStatus.RUNNING
    stage: str = ''
    stage_length: int = 0
    # 0.0..1.0 within the current stage; the client combines it with `stage`.
    stage_progress: float = 0.0
    error: str = ''
    _cancel: threading.Event = field(default_factory=threading.Event, repr=False)

    def request_cancel(self) -> None:
        self._cancel.set()

    @property
    def cancel_requested(self) -> bool:
        return self._cancel.is_set()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'project': self.project_name,
            'output': self.output,
            'status': self.status.value,
            'stage': self.stage,
            'stage_length': self.stage_length,
            'stage_progress': self.stage_progress,
            'error': self.error,
        }


class JobManager:
    """Thread-safe registry of render jobs, keyed by id, with at most one
    RUNNING job per project."""

    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}
        # project name -> id of its current (RUNNING) job, if any
        self._active_by_project: Dict[str, str] = {}
        self._lock = threading.Lock()

    def create(self, project_name: str, output: str) -> Job:
        """Register a new RUNNING job for a project.

        Raises RuntimeError if that project already has a running job - two
        concurrent renders would race on the same per-thread workdirs.
        """
        with self._lock:
            active_id = self._active_by_project.get(project_name)
            if active_id is not None:
                active = self._jobs.get(active_id)
                if active is not None and active.status == JobStatus.RUNNING:
                    raise RuntimeError(
                        f'A render is already running for project "{project_name}"')
            job = Job(id=uuid.uuid4().hex, project_name=project_name, output=output)
            self._jobs[job.id] = job
            self._active_by_project[project_name] = job.id
            return job

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def finish(self, job_id: str, status: JobStatus, error: str = '') -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = status
            job.error = error
            # release the per-project slot so a new render can start
            if self._active_by_project.get(job.project_name) == job_id:
                del self._active_by_project[job.project_name]
