from threading import Event


class CancellationToken:
    def __init__(self) -> None:
        self._event = Event()

    def cancel(self) -> None:
        self._event.set()

    def is_set(self) -> bool:
        return self._event.is_set()


class PipelineCancelled(Exception):
    """Raised at a stage boundary when a caller cancels a run."""
