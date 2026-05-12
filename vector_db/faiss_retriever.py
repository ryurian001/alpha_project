from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

try:
    import faiss
except ImportError as exc:
    raise ImportError(
        "FAISS is required for vector search. Install it with `pip install faiss-cpu` or `pip install faiss` depending on your platform."
    ) from exc

try:
    from sentence_transformers import SentenceTransformer
except ImportError as exc:
    raise ImportError(
        "sentence-transformers is required for embedding generation. Install it with `pip install sentence-transformers`."
    ) from exc

ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_INDEX_PATH = ROOT_DIR / "kmu_notice_index.faiss"
DEFAULT_STORE_PATH = ROOT_DIR / "kmu_notice_store.pkl"
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def load_store(store_path: Path = DEFAULT_STORE_PATH) -> Dict[str, Any]:
    """Load FAISS metadata store saved as a pickle file."""
    if not store_path.exists():
        raise FileNotFoundError(f"Store file not found: {store_path}")
    with store_path.open("rb") as f:
        store = pickle.load(f)
    if not isinstance(store, dict):
        raise ValueError("Loaded store must be a dict containing metadatas and documents.")
    return store


def load_faiss_index(index_path: Path = DEFAULT_INDEX_PATH) -> faiss.Index:
    """Load FAISS index from disk."""
    if not index_path.exists():
        raise FileNotFoundError(f"FAISS index file not found: {index_path}")
    return faiss.read_index(str(index_path))


def embed_query(query: str, model_name: str = DEFAULT_EMBEDDING_MODEL, normalize: bool = False) -> np.ndarray:
    """Generate a vector embedding for a query string."""
    model = SentenceTransformer(model_name)
    vector = model.encode(query, convert_to_numpy=True)
    vector = np.asarray(vector, dtype=np.float32)
    if normalize:
        faiss.normalize_L2(vector)
    return vector


def retrieve(
    query: str,
    top_k: int = 5,
    index_path: Path = DEFAULT_INDEX_PATH,
    store_path: Path = DEFAULT_STORE_PATH,
    embedding_model_name: str = DEFAULT_EMBEDDING_MODEL,
    normalize_embedding: bool = False,
) -> List[Dict[str, Any]]:
    """Search FAISS index and return top-k metadata-enriched results."""
    index = load_faiss_index(index_path)
    store = load_store(store_path)
    query_vector = embed_query(query, embedding_model_name, normalize=normalize_embedding)
    query_vector = query_vector.reshape(1, -1)

    distances, indices = index.search(query_vector, top_k)
    distances = distances[0].tolist()
    indices = indices[0].tolist()

    is_inner_product = index.metric_type == faiss.METRIC_INNER_PRODUCT
    results: List[Dict[str, Any]] = []

    for rank, (distance, matched_index) in enumerate(zip(distances, indices), start=1):
        if matched_index < 0 or matched_index >= len(store["metadatas"]):
            continue

        metadata = store["metadatas"][matched_index]
        chunk_text = store["documents"][matched_index]

        result = {
            "rank": rank,
            "score": float(distance) if is_inner_product else None,
            "distance": float(distance) if not is_inner_product else None,
            "metric": "inner_product" if is_inner_product else "l2",
            "title": metadata.get("title", ""),
            "date": metadata.get("date", ""),
            "category": metadata.get("category", ""),
            "url": metadata.get("url", ""),
            "source": metadata.get("source", ""),
            "chunk_id": metadata.get("chunk_id", ""),
            "chunk_text": chunk_text,
        }
        results.append(result)

    return results


def build_context(results: List[Dict[str, Any]], max_chunks: int = 5) -> str:
    """Build a single text context from top-k search results for RAG prompt input."""
    if not results:
        return ""

    sections = []
    for item in results[:max_chunks]:
        snippet = item["chunk_text"].strip()
        sections.append(
            """제목: {title}
날짜: {date}
카테고리: {category}
URL: {url}
본문:
{chunk_text}""".format(
                title=item["title"],
                date=item["date"],
                category=item["category"],
                url=item["url"] or "(URL 없음)",
                chunk_text=snippet,
            )
        )

    return "\n\n---\n\n".join(sections)


def generate_answer(query: str, context: str) -> str:
    """Generate a prompt template for a downstream LLM based on search context."""
    prompt = f"""아래 공지사항 정보를 바탕으로 사용자 질문에 답변하세요.

사용자 질문: {query}

검색 결과 정보:
{context}

요청:
- 답변에는 공지 제목, 날짜, 핵심 내용, URL을 포함하세요.
- 검색 결과에 없는 내용은 추측하지 마세요.
- 관련 내용이 없으면 "관련 공지가 없습니다."라고 답변하세요.
"""
    return prompt


def search_quality_guidelines() -> List[str]:
    """Return a checklist for manual search quality inspection."""
    return [
        "질문의 의도와 검색 결과의 category가 일치하는가?",
        "최신 공지가 우선 노출되는가?",
        "title과 chunk_text가 질문과 관련 있는가?",
        "동일 공지 chunk가 너무 많이 중복 노출되지 않는가?",
        "url metadata가 정상 출력되는가?",
    ]
