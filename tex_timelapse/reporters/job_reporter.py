from typing import Optional

from flask_socketio import SocketIO  # type: ignore

from tex_timelapse.jobs import Job
from tex_timelapse.reporter import Reporter
from tex_timelapse.snapshot import Snapshot


class JobReporter(Reporter):
    """Reporter for an async render job.

    Does what WebReporter does - pushes stage/progress/log events over
    Socket.IO for a live UI - and additionally records the latest progress
    onto the Job, so a client that polls GET /api/jobs/<id> (or reconnects
    after missing socket events) can still see where the render is. Every
    emitted event carries the job id so a client can tell concurrent jobs
    apart.
    """

    def __init__(self, socketio: SocketIO, job: Job):
        self.socketio = socketio
        self.job = job

    def set_stage(self, name: str, length: int) -> None:
        self.job.stage = name
        self.job.stage_length = length
        self.job.stage_progress = 0.0
        self.socketio.emit('stage', {'job': self.job.id, 'stage': name, 'length': length})

    def add_progress(self, snapshot: Snapshot) -> None:
        self.socketio.emit('add_progress', {'job': self.job.id, 'snapshot': snapshot.to_dict()})

    def update_progress(self, snapshot: Snapshot) -> None:
        self.socketio.emit('add_progress', {'job': self.job.id, 'snapshot': snapshot.to_dict()})

    def set_progress(self, num: float) -> None:
        self.job.stage_progress = num
        self.socketio.emit('set_progress', {'job': self.job.id, 'set': num})

    def log(self, msg: str, snapshot: Optional[Snapshot] = None) -> None:
        snapshot_sha = snapshot.commit_sha if snapshot is not None else None
        self.socketio.emit('log', {'job': self.job.id, 'msg': msg, 'snapshot_sha': snapshot_sha})
