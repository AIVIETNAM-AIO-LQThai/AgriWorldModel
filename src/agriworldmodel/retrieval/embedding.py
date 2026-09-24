from typing import Protocol

EMBEDDING_DIMENSION = 1024
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-m3"

class DenseEmbedder(Protocol):
    """
    Interface used by AgriWorldModel for dense embeddings.

    Retrieval code depends on this interface rather than
    directly depending on BGE-M3.
    """
    model_name: str
    dimension: int

    def embed_documents(
        self, texts: list[str]
    ) -> list[list[float]]:
        ...

    def embed_query(
        self, text: str
    ) -> list[float]:
        ...

class BGEM3DenseEmbedder:
    """
    Production dense embedder backed by BAAI/bge-m3.

    Model loading is intentionally lazy: constructing this class
    loads the actual embedding model, so tests should use a fake
    DenseEmbedder instead.
    """
    model_name = DEFAULT_EMBEDDING_MODEL
    dimension = EMBEDDING_DIMENSION

    def __init__(
        self, *, use_fp16: bool = False, devices: list[str] | None = None
    ):
        from FlagEmbedding import BGEM3FlagModel
        kwargs = {
            "use_fp16": use_fp16,
        }
        if devices is not None:
            kwargs["devices"] = devices

        self._model = BGEM3FlagModel(
            self.model_name, **kwargs
        )

    def embed_documents(
        self, texts: list[str]
    ) -> list[list[float]]:
        if not texts:
            return []

        output = self._model.encode(
            texts, return_dense=True, return_sparse=False, return_colbert_vecs=False
        )

        return output["dense_vecs"].tolist()

    def embed_query(
        self, text: str
    ) -> list[float]:
        vectors = self.embed_documents([text])
        return vectors[0]