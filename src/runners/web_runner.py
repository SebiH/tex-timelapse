from ..reporter import Reporter

class WebReporter(Reporter):
    def __init__(self):
        pass
        # with alive_bar(100, title='Loading...', bar='blocks') as bar:
        #     for i in range(100):
        #         time.sleep(0.01)
        #         bar()

    def set_stage(self, name: str, length: int) -> None:
        pass

    def add_progress(self) -> None:
        pass

    def set_progress(self, num: float) -> None:
        pass

    def log(self, msg: str) -> None:
        pass
