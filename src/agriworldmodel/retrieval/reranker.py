from typing import Protocol

DEFAULT_RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"

class Reranker(Protocol):
    model_name: str

    def score(
        self, *, query: str, passages: list[str],
    ) -> list[float]:
        ...

class BGEReranker:
    """
    Production reranker backed by BAAI/bge-reranker-v2-m3.

    Model loading is lazy. Unit tests should use a fake
    Reranker rather than loading the real model.
    """
    model_name = DEFAULT_RERANKER_MODEL

    def __init__(
        self, *, use_fp16: bool = False, devices: list[str] | None = None
    ):
        from FlagEmbedding import FlagReranker

        kwargs = {
            "use_fp16": use_fp16
        }

        if devices is not None:
            kwargs["devices"] = devices

        self._model = FlagReranker(
            self.model_name, **kwargs
        )

    def score(
        self, *, query: str, passages: list[str]
    ) -> list[float]:
        if not passages:
            return []

        pairs = [
            [query, passage] for passage in passages
        ]
        scores = self._model.compute_score(pairs, normalize=True)

        # Defensive handling in case the backend returns
        # one scalar for a single input pair.
        if isinstance(scores, (int, float)):
            return [float(scores)]

        return [float(score) for score in scores]