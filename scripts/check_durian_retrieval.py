from agriworldmodel.db.session import SessionLocal
from agriworldmodel.retrieval.dense import search_dense_text
from agriworldmodel.retrieval.embedding import BGEM3DenseEmbedder
from agriworldmodel.retrieval.hybrid import search_hybrid_chunks
from agriworldmodel.retrieval.lexical import search_lexical_chunks
from agriworldmodel.retrieval.rerank import search_reranked_chunks, rerank_hybrid_chunks
from agriworldmodel.retrieval.reranker import BGEReranker

QUERY = (
    "How do organic manure and foliar fertilization affect "
    "soil fertility, leaf nutrient status, fruit yield, "
    "and physiological disorders in durian?"
)

RERANK_QUERY = (
    "Find passages that report observed experimental results "
    "or conclusions about the effects of organic manure and "
    "foliar fertilization on soil fertility, leaf nutrient "
    "status, fruit yield, fruit quality, or physiological "
    "disorders in durian. Prefer passages that state measured "
    "effects, comparisons, outcomes, correlations, or conclusions "
    "over passages that only describe background, experimental "
    "methods, instruments, or statistical procedures."
)

def preview(text: str, limit: int = 700) -> str:
    text = text.replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."

def print_results(title, results):
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)

    if not results:
        print("NO RESULTS")
        return

    for rank, result in enumerate(results, start=1):
        print()
        print(f"#{rank}")
        print("chunk_id:", result.chunk_id)
        print("source:", result.source_title)
        print("locator:", result.locator)

        if hasattr(result, "score"):
            print("score:", round(result.score, 6))
        if hasattr(result, "lexical_rank"):
            print("lexical_rank:", result.lexical_rank)
        if hasattr(result, "dense_rank"):
            print("dense_rank:", result.dense_rank)
        if hasattr(result, "hybrid_rank"):
            print("hybrid_rank:", result.hybrid_rank)
        if hasattr(result, "rrf_score"):
            print("rrf_score:", round(result.rrf_score, 6))
        if hasattr(result, "rerank_score"):
            print("rerank_score:", round(result.rerank_score, 6))

        print()
        print(preview(result.content))

def main() -> None:
    print("Loading BGE-M3 on CUDA...")
    embedder = BGEM3DenseEmbedder(use_fp16=True, devices=["cuda:0"])
    print("Embedding model:", embedder.model_name)

    print()
    print("Query:")
    print(QUERY)

    with SessionLocal() as session:
        lexical = search_lexical_chunks(
            session, query_text=QUERY,
            crop="durian", limit=5
        )
        dense = search_dense_text(
            session, query_text=QUERY,
            embedder=embedder,
            crop="durian", limit=5
        )
        hybrid = search_hybrid_chunks(
            session, query_text=QUERY,
            embedder=embedder,
            crop="durian", limit=5,
            candidate_limit=20
        )

        print_results("LEXICAL TOP 5", lexical)
        print_results("DENSE TOP 5", dense)
        print_results("RRF HYBRID TOP 5", hybrid)

        print()
        print("Loading bge-reranker-v2-m3...")

        reranker = BGEReranker(use_fp16=True, devices=["cuda:0"])

        # Retrieve all 34 chunks using the ORIGINAL user question.
        candidates = search_hybrid_chunks(
            session, query_text=QUERY,
            embedder=embedder,
            crop="durian", limit=34,
            candidate_limit=34
        )

        # Rank those same candidates using the answer-seeking objective.
        reranked = rerank_hybrid_chunks(
            query_text=RERANK_QUERY,
            candidates=candidates,
            reranker=reranker,
            limit=10,
        )

        print_results("ANSWER-SEEKING RERANK TOP 10", reranked)

if __name__ == "__main__":
    main()