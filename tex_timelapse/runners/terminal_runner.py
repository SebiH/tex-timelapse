from alive_progress import alive_bar
from tex_timelapse.reporter import Reporter

class TerminalReporter(Reporter):
    def __init__(self):
        self.context = None
        pass

    def set_stage(self, name: str, length: int) -> None:
        if self.context is not None:
            type(self.context).__exit__(self.context, None, None, None)

        self.context = alive_bar(length, title=name)
        self.bar = type(self.context).__enter__(self.context)
        pass

    def add_progress(self) -> None:
        self.bar()
        pass

    def set_progress(self, num: float) -> None:
        self.bar(num)
        pass

    def log(self, msg: str) -> None:
        print(msg)
        pass


def run():
    pass
