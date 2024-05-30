from flask_socketio import SocketIO # type: ignore
from typing import Optional
from tex_timelapse.reporter import Reporter
from tex_timelapse.snapshot import Snapshot

class WebReporter(Reporter):
    def __init__(self, socketio: SocketIO):
        self.socketio = socketio

    def set_stage(self, name: str, length: int) -> None:
        self.socketio.emit('stage', { 'stage': name, 'length': length })

    def add_progress(self, snapshot: Snapshot) -> None:
        self.socketio.emit('add_progress', {
            'snapshot': snapshot.to_dict()
        })

    def update_progress(self, snapshot: Snapshot) -> None:
        self.socketio.emit('add_progress', {
            'snapshot': snapshot.to_dict()
        })

    def set_progress(self, num: float) -> None:
        self.socketio.emit('set_progress', { 'set': num })

    def log(self, msg: str, snapshot: Optional[Snapshot] = None) -> None:
        snapshot_sha = snapshot.commit_sha if snapshot is not None else None
        self.socketio.emit('log', { 'msg': msg, 'snapshot_sha': snapshot_sha })
