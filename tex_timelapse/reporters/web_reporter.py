from flask_socketio import SocketIO
from tex_timelapse.reporter import Reporter

class WebReporter(Reporter):
    def __init__(self, socketio: SocketIO):
        self.socketio = socketio

    def set_stage(self, name: str, length: int) -> None:
        self.socketio.emit('log', { 'msg': f'stage: {name}, length: {length}' })

    def add_progress(self) -> None:
        self.socketio.emit('log', { 'msg': 'progress' })

    def set_progress(self, num: float) -> None:
        self.socketio.emit('log', { 'msg': 'progress: ' + str(num) })

    def log(self, msg: str) -> None:
        self.socketio.emit('log', { 'msg': msg })
