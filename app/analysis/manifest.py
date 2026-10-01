from dataclasses import asdict, dataclass, field
from typing import Any
import time
from app.analysis.status import ResultStatus


@dataclass
class OperationRecord:
    name: str
    status: ResultStatus
    parameters: dict[str, Any] = field(default_factory=dict)
    elapsed_ms: float = 0
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {"status": self.status.value}


class ProcessingManifest:
    def __init__(self) -> None:
        self.operations: list[OperationRecord] = []

    def operation(self, name: str, parameters: dict[str, Any] | None = None):
        started = time.perf_counter()
        record = OperationRecord(name, ResultStatus.SUCCESS, parameters or {})
        self.operations.append(record)

        class Context:
            def __enter__(inner):
                return record

            def __exit__(inner, exc_type, exc, tb):
                record.elapsed_ms = (time.perf_counter() - started) * 1000
                if exc:
                    record.status = ResultStatus.FAILED
                    record.message = str(exc)
                return False

        return Context()

    def to_dict(self) -> dict[str, Any]:
        return {"operations": [operation.to_dict() for operation in self.operations]}
