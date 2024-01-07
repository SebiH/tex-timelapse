from flask_socketio import SocketIO
from ..reporter import Reporter

class WebReporter(Reporter):
    def __init__(self, socketio: SocketIO):
        self.socketio = socketio
        pass
        # with alive_bar(100, title='Loading...', bar='blocks') as bar:
        #     for i in range(100):
        #         time.sleep(0.01)
        #         bar()

    def set_stage(self, name: str, length: int) -> None:
        self.socketio.emit('log', { 'msg': f'stage: {name}, length: {length}' })
        pass

    def add_progress(self) -> None:
        self.socketio.emit('log', { 'msg': 'progress' })
        pass

    def set_progress(self, num: float) -> None:
        self.socketio.emit('log', { 'msg': 'progress: ' + str(num) })
        pass

    def log(self, msg: str) -> None:
        self.socketio.emit('log', { 'msg': msg })
