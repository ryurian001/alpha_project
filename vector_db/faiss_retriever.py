from __future__ import annotations

import json
import logging
import math
import pickle
import re
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List

import numpy as np

try:
    import faiss
except ImportError as exc:
    raise ImportError(
        "FAISS is required for vector search. Install it with `pip install faiss-cpu` or `pip install faiss` depending on your platform."
    ) from exc

try:
    from sentence_transformers import CrossEncoder, SentenceTransformer
except ImportError as exc:
    raise ImportError(
        "sentence-transformers is required for embedding generation. Install it with `pip install sentence-transformers`."
    ) from exc

ROOT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT_DIR.parent
DEFAULT_INDEX_PATH = ROOT_DIR / "kmu_notice_index.faiss"
DEFAULT_STORE_PATH = ROOT_DIR / "kmu_notice_store.pkl"
DEFAULT_CHUNKS_PATH = PROJECT_ROOT / "data" / "chunks" / "notices_chunks.jsonl"
DEFAULT_CLEAN_PATH = PROJECT_ROOT / "data" / "clean" / "notices_clean.jsonl"
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
DEFAULT_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
NO_RELEVANT_NOTICE_MESSAGE = "관련 공지가 없습니다."
DEFAULT_RELEVANCE_THRESHOLD = 0.15

logger = logging.getLogger(__name__)

CATEGORY_ALIASES = {
    "학사공지": ("학사공지", "학사", "수강", "졸업", "휴학", "복학", "성적"),
    "취업공지": ("취업공지", "취업", "채용", "인턴", "현장실습", "모집"),
    "장학공지": ("장학공지", "장학", "장학금"),
    "특강 및 행사": ("특강 및 행사", "특강", "행사", "세미나", "설명회"),
    "프로그램 및 행사": ("프로그램 및 행사", "프로그램", "SW중심대학 행사"),
    "산학협력": ("산학협력", "산학", "협력", "기업"),
    "학생지원": ("학생지원", "학생지원", "지원사업"),
    "기타": ("기타",),
}

TOKEN_RE = re.compile(r"[가-힣A-Za-z0-9]+")
NOTICE_DATE_RE = re.compile(r"(\d{2})\.(\d{1,2})\.(\d{1,2})")
YEAR_RE = re.compile(r"(20\d{2})\s*년")


@dataclass(frozen=True)
class DateFilter:
    label: str
    start: date | None = None
    end: date | None = None
    year: int | None = None


class BM25Index:
    """Small in-memory BM25 implementation for JSONL-sized notice corpora."""

    def __init__(self, documents: list[str], k1: float = 1.5, b: float = 0.75):
        self.documents = documents
        self.k1 = k1
        self.b = b
        self.tokenized = [tokenize(doc) for doc in documents]
        self.doc_len = [len(tokens) for tokens in self.tokenized]
        self.avgdl = sum(self.doc_len) / len(self.doc_len) if self.doc_len else 0.0
        self.doc_freq: dict[str, int] = {}
        for tokens in self.tokenized:
            for token in set(tokens):
                self.doc_freq[token] = self.doc_freq.get(token, 0) + 1

    def score(self, query: str, doc_index: int) -> float:
        tokens = self.tokenized[doc_index]
        if not tokens:
            return 0.0

        query_tokens = tokenize(query)
        if not query_tokens:
            return 0.0

        tf: dict[str, int] = {}
        for token in tokens:
            tf[token] = tf.get(token, 0) + 1

        score = 0.0
        total_docs = len(self.tokenized)
        doc_len = self.doc_len[doc_index]
        for token in query_tokens:
            frequency = tf.get(token, 0)
            if frequency == 0:
                continue

            df = self.doc_freq.get(token, 0)
            idf = math.log(1 + (total_docs - df + 0.5) / (df + 0.5))
            denominator = frequency + self.k1 * (1 - self.b + self.b * doc_len / (self.avgdl or 1.0))
            score += idf * frequency * (self.k1 + 1) / denominator
        return score

    def search(self, query: str, candidate_indices: Iterable[int], top_k: int) -> dict[int, float]:
        scored = [(index, self.score(query, index)) for index in candidate_indices]
        scored = [(index, score) for index, score in scored if score > 0]
        scored.sort(key=lambda item: item[1], reverse=True)
        return dict(scored[:top_k])


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text or "")]


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


def load_chunk_metadata(chunks_path: Path = DEFAULT_CHUNKS_PATH) -> dict[str, dict[str, Any]]:
    """Load richer JSONL chunk metadata keyed by chunk_id when available."""
    if not chunks_path.exists():
        return {}

    metadata_by_chunk_id: dict[str, dict[str, Any]] = {}
    with chunks_path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            row = json.loads(line)
            metadata = dict(row.get("metadata") or {})
            chunk_id = row.get("chunk_id") or metadata.get("chunk_id")
            if not chunk_id:
                continue
            metadata.update(
                {
                    "chunk_id": chunk_id,
                    "notice_id": row.get("notice_id") or metadata.get("notice_id", ""),
                    "chunk_index": row.get("chunk_index", metadata.get("chunk_index", 0)),
                }
            )
            metadata_by_chunk_id[chunk_id] = metadata
    return metadata_by_chunk_id


def load_notice_metadata(clean_path: Path = DEFAULT_CLEAN_PATH) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    """Load notice-level metadata keyed by title/date/source/category for stale stores."""
    if not clean_path.exists():
        return {}

    metadata_by_notice_key: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    with clean_path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            row = json.loads(line)
            key = (
                row.get("title", ""),
                row.get("date", ""),
                row.get("source", ""),
                row.get("category", ""),
            )
            metadata_by_notice_key[key] = {
                "url": row.get("url", ""),
                "attachments": row.get("attachments", []),
                "attached_links": row.get("attached_links", []),
                "attached_images": row.get("attached_images", []),
                "created_at": row.get("created_at", ""),
                "updated_at": row.get("updated_at", ""),
            }
    return metadata_by_notice_key


def parse_notice_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None

    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").date()
    except ValueError:
        pass

    match = NOTICE_DATE_RE.search(text)
    if not match:
        return None

    year, month, day = match.groups()
    try:
        return date(2000 + int(year), int(month), int(day))
    except ValueError:
        return None


def enrich_metadata_store(
    store: Dict[str, Any], chunks_path: Path = DEFAULT_CHUNKS_PATH
) -> Dict[str, Any]:
    """Backfill production metadata fields without requiring an index rebuild."""
    chunk_metadata = load_chunk_metadata(chunks_path)
    notice_metadata = load_notice_metadata()
    metadatas = store.get("metadatas", [])
    ids = store.get("ids", [])

    for index, metadata in enumerate(metadatas):
        chunk_id = metadata.get("chunk_id") or (ids[index] if index < len(ids) else "")
        enriched = dict(chunk_metadata.get(chunk_id, {}))
        enriched.update({key: value for key, value in metadata.items() if value not in ("", None, [])})

        notice_key = (
            enriched.get("title", ""),
            enriched.get("date", ""),
            enriched.get("source", ""),
            enriched.get("category", ""),
        )
        for key, value in notice_metadata.get(notice_key, {}).items():
            if enriched.get(key) in ("", None, []):
                enriched[key] = value

        notice_date = parse_notice_date(enriched.get("created_at") or enriched.get("date"))
        created_at = notice_date.isoformat() if notice_date else ""
        enriched.setdefault("chunk_id", chunk_id)
        enriched.setdefault("notice_id", chunk_id.rsplit("_", 1)[0] if "_" in chunk_id else chunk_id)
        enriched.setdefault("chunk_index", int(chunk_id.rsplit("_", 1)[1]) if "_" in chunk_id and chunk_id.rsplit("_", 1)[1].isdigit() else 0)
        enriched.setdefault("attachments", [])
        enriched.setdefault("attached_links", [])
        enriched.setdefault("attached_images", [])
        enriched.setdefault("created_at", created_at)
        enriched.setdefault("updated_at", created_at)
        metadatas[index] = enriched

    store["metadatas"] = metadatas
    return store


def embed_query(query: str, model_name: str = DEFAULT_EMBEDDING_MODEL, normalize: bool = False) -> np.ndarray:
    """Generate a vector embedding for a query string."""
    model = SentenceTransformer(model_name)
    vector = model.encode(query, convert_to_numpy=True)
    vector = np.asarray(vector, dtype=np.float32)
    if normalize:
        faiss.normalize_L2(vector.reshape(1, -1))
    return vector


def infer_category_filter(query: str, explicit_category: str | None = None) -> str | None:
    if explicit_category:
        return explicit_category

    compact_query = re.sub(r"\s+", "", query)
    for category in sorted(CATEGORY_ALIASES, key=lambda value: len(value.replace(" ", "")), reverse=True):
        if category.replace(" ", "") in compact_query:
            return category

    query_tokens = set(tokenize(query))
    matches: list[tuple[int, str]] = []
    for category, aliases in CATEGORY_ALIASES.items():
        for alias in aliases:
            compact_alias = alias.replace(" ", "")
            if len(compact_alias) <= 2 and compact_alias.lower() not in query_tokens:
                continue
            if compact_alias in compact_query:
                matches.append((len(compact_alias), category))

    if not matches:
        return None
    matches.sort(key=lambda item: item[0], reverse=True)
    return matches[0][1]


def previous_semester_range(today: date) -> tuple[date, date]:
    if today.month >= 9:
        return date(today.year, 3, 1), date(today.year, 8, 31)
    if today.month >= 3:
        return date(today.year - 1, 9, 1), date(today.year, 2, 28)
    return date(today.year - 1, 3, 1), date(today.year - 1, 8, 31)


def parse_date_filter(query: str, today: date | None = None) -> DateFilter | None:
    today = today or date.today()

    year_match = YEAR_RE.search(query)
    if year_match:
        year = int(year_match.group(1))
        return DateFilter(label=f"{year}년", year=year)

    if "작년" in query:
        year = today.year - 1
        return DateFilter(label="작년", year=year)

    if "올해" in query or "금년" in query:
        return DateFilter(label="올해", year=today.year)

    if "지난 학기" in query or "이전 학기" in query:
        start, end = previous_semester_range(today)
        return DateFilter(label="지난 학기", start=start, end=end)

    if "최근" in query or "최신" in query:
        return DateFilter(label="최근", start=today - timedelta(days=180), end=today)

    return None


def metadata_matches(metadata: dict[str, Any], category: str | None, date_filter: DateFilter | None) -> bool:
    if category and metadata.get("category") != category:
        return False

    if not date_filter:
        return True

    notice_date = parse_notice_date(metadata.get("created_at") or metadata.get("date"))
    if not notice_date:
        return False

    if date_filter.year and notice_date.year != date_filter.year:
        return False
    if date_filter.start and notice_date < date_filter.start:
        return False
    if date_filter.end and notice_date > date_filter.end:
        return False
    return True


def min_max_normalize(scores: dict[int, float]) -> dict[int, float]:
    if not scores:
        return {}
    values = list(scores.values())
    low = min(values)
    high = max(values)
    if math.isclose(low, high):
        return {index: 1.0 for index in scores}
    return {index: (score - low) / (high - low) for index, score in scores.items()}


def vector_search_candidates(
    query: str,
    index: faiss.Index,
    store: Dict[str, Any],
    candidate_k: int,
    embedding_model_name: str,
    normalize_embedding: bool,
    allowed_indices: set[int],
) -> dict[int, float]:
    query_vector = embed_query(query, embedding_model_name, normalize=normalize_embedding).reshape(1, -1)
    if query_vector.shape[1] != index.d:
        raise ValueError(
            "Embedding dimension mismatch: "
            f"query model '{embedding_model_name}' produced {query_vector.shape[1]} dims, "
            f"but FAISS index expects {index.d}. Use the same embedding model used to build the index."
        )
    search_k = min(max(candidate_k * 4, candidate_k), index.ntotal)
    distances, indices = index.search(query_vector, search_k)

    is_inner_product = index.metric_type == faiss.METRIC_INNER_PRODUCT
    scores: dict[int, float] = {}
    for distance, matched_index in zip(distances[0].tolist(), indices[0].tolist()):
        if matched_index < 0 or matched_index not in allowed_indices:
            continue
        scores[matched_index] = float(distance) if is_inner_product else 1.0 / (1.0 + float(distance))
        if len(scores) >= candidate_k:
            break
    return scores


def build_chunk_lookup(store: Dict[str, Any]) -> dict[tuple[str, int], int]:
    lookup: dict[tuple[str, int], int] = {}
    for index, metadata in enumerate(store.get("metadatas", [])):
        notice_id = metadata.get("notice_id")
        chunk_index = metadata.get("chunk_index")
        if notice_id is None or chunk_index is None:
            continue
        lookup[(str(notice_id), int(chunk_index))] = index
    return lookup


def expand_chunk_text(store: Dict[str, Any], matched_index: int, window: int = 1) -> str:
    metadata = store["metadatas"][matched_index]
    notice_id = str(metadata.get("notice_id", ""))
    chunk_index = int(metadata.get("chunk_index", 0))
    lookup = build_chunk_lookup(store)

    texts = []
    for neighbor_index in range(chunk_index - window, chunk_index + window + 1):
        store_index = lookup.get((notice_id, neighbor_index))
        if store_index is None:
            continue
        text = store["documents"][store_index].strip()
        if text and text not in texts:
            texts.append(text)
    return "\n\n".join(texts)


def make_result(
    rank: int,
    matched_index: int,
    hybrid_score: float,
    vector_score: float,
    bm25_score: float,
    store: Dict[str, Any],
    expanded_chunk_text: str | None = None,
    rerank_score: float | None = None,
) -> Dict[str, Any]:
    metadata = store["metadatas"][matched_index]
    chunk_text = store["documents"][matched_index]
    return {
        "rank": rank,
        "score": hybrid_score,
        "hybrid_score": hybrid_score,
        "vector_score": vector_score,
        "bm25_score": bm25_score,
        "rerank_score": rerank_score,
        "metric": "hybrid",
        "title": metadata.get("title", ""),
        "date": metadata.get("date", ""),
        "category": metadata.get("category", ""),
        "url": metadata.get("url", ""),
        "source": metadata.get("source", ""),
        "notice_id": metadata.get("notice_id", ""),
        "chunk_index": metadata.get("chunk_index", 0),
        "chunk_id": metadata.get("chunk_id", ""),
        "attachments": metadata.get("attachments", []),
        "attached_links": metadata.get("attached_links", []),
        "attached_images": metadata.get("attached_images", []),
        "created_at": metadata.get("created_at", ""),
        "updated_at": metadata.get("updated_at", ""),
        "chunk_text": chunk_text,
        "expanded_chunk_text": expanded_chunk_text or chunk_text,
    }


def rerank_candidates(
    query: str,
    candidates: list[tuple[int, float, float, float]],
    store: Dict[str, Any],
    model_name: str,
) -> list[tuple[int, float, float, float, float]]:
    if not candidates:
        return []

    model = CrossEncoder(model_name)
    pairs = [(query, store["documents"][index]) for index, *_ in candidates]
    scores = model.predict(pairs)
    reranked = [
        (index, hybrid_score, vector_score, bm25_score, float(rerank_score))
        for (index, hybrid_score, vector_score, bm25_score), rerank_score in zip(candidates, scores)
    ]
    reranked.sort(key=lambda item: item[4], reverse=True)
    return reranked


def retrieve(
    query: str,
    top_k: int = 5,
    index_path: Path = DEFAULT_INDEX_PATH,
    store_path: Path = DEFAULT_STORE_PATH,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    embedding_model_name: str = DEFAULT_EMBEDDING_MODEL,
    normalize_embedding: bool = False,
    category: str | None = None,
    candidate_k: int = 50,
    hybrid_alpha: float = 0.65,
    max_chunks_per_notice: int = 1,
    expand_context: bool = True,
    expansion_window: int = 1,
    enable_rerank: bool = False,
    reranker_model_name: str = DEFAULT_RERANKER_MODEL,
    relevance_threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
    today: date | None = None,
) -> List[Dict[str, Any]]:
    """Hybrid retrieval with metadata filters, relevance gate, deduplication, expansion, and optional reranking."""
    started_at = time.perf_counter()
    index = load_faiss_index(index_path)
    store = enrich_metadata_store(load_store(store_path), chunks_path=chunks_path)
    metadatas = store.get("metadatas", [])

    category_filter = infer_category_filter(query, category)
    date_filter = parse_date_filter(query, today=today)
    allowed_indices = {
        index
        for index, metadata in enumerate(metadatas)
        if metadata_matches(metadata, category_filter, date_filter)
    }
    if not allowed_indices:
        logger.info(
            "retrieval.no_candidates query=%r category=%r date_filter=%r latency_ms=%.2f",
            query,
            category_filter,
            date_filter,
            (time.perf_counter() - started_at) * 1000,
        )
        return []

    candidate_k = max(candidate_k, top_k * 5)
    vector_scores = vector_search_candidates(
        query,
        index,
        store,
        candidate_k=candidate_k,
        embedding_model_name=embedding_model_name,
        normalize_embedding=normalize_embedding,
        allowed_indices=allowed_indices,
    )
    bm25 = BM25Index(store["documents"])
    bm25_scores = bm25.search(query, allowed_indices, top_k=candidate_k)

    vector_norm = min_max_normalize(vector_scores)
    bm25_norm = min_max_normalize(bm25_scores)
    candidate_indices = set(vector_scores) | set(bm25_scores)

    candidates: list[tuple[int, float, float, float]] = []
    for matched_index in candidate_indices:
        vector_score = vector_norm.get(matched_index, 0.0)
        bm25_score = bm25_norm.get(matched_index, 0.0)
        hybrid_score = hybrid_alpha * vector_score + (1 - hybrid_alpha) * bm25_score
        if hybrid_score < relevance_threshold:
            continue
        candidates.append((matched_index, hybrid_score, vector_score, bm25_score))
    candidates.sort(key=lambda item: item[1], reverse=True)

    if not candidates:
        logger.info(
            "retrieval.gated query=%r category=%r date_filter=%r threshold=%.3f latency_ms=%.2f",
            query,
            category_filter,
            date_filter,
            relevance_threshold,
            (time.perf_counter() - started_at) * 1000,
        )
        return []

    if enable_rerank:
        reranked = rerank_candidates(query, candidates[:candidate_k], store, reranker_model_name)
        ordered = [(index, hybrid, vector, bm25, rerank) for index, hybrid, vector, bm25, rerank in reranked]
    else:
        ordered = [(index, hybrid, vector, bm25, None) for index, hybrid, vector, bm25 in candidates]

    results: list[dict[str, Any]] = []
    per_notice_counts: dict[str, int] = {}
    for matched_index, hybrid_score, vector_score, bm25_score, rerank_score in ordered:
        metadata = metadatas[matched_index]
        notice_id = str(metadata.get("notice_id", metadata.get("chunk_id", matched_index)))
        if per_notice_counts.get(notice_id, 0) >= max_chunks_per_notice:
            continue

        expanded = expand_chunk_text(store, matched_index, expansion_window) if expand_context else None
        results.append(
            make_result(
                len(results) + 1,
                matched_index,
                hybrid_score,
                vector_score,
                bm25_score,
                store,
                expanded_chunk_text=expanded,
                rerank_score=rerank_score,
            )
        )
        per_notice_counts[notice_id] = per_notice_counts.get(notice_id, 0) + 1
        if len(results) >= top_k:
            break

    latency_ms = (time.perf_counter() - started_at) * 1000
    for result in results:
        result["retrieval_latency_ms"] = latency_ms
        result["relevance_threshold"] = relevance_threshold

    logger.info(
        "retrieval.completed query=%r results=%d category=%r date_filter=%r latency_ms=%.2f rerank=%s",
        query,
        len(results),
        category_filter,
        date_filter,
        latency_ms,
        enable_rerank,
    )
    return results


def build_context(results: List[Dict[str, Any]], max_chunks: int = 5) -> str:
    """Build a single text context from retrieved chunks for RAG prompt input."""
    if not results:
        return ""

    sections = []
    for item in results[:max_chunks]:
        snippet = item.get("expanded_chunk_text") or item["chunk_text"]
        resources = []
        for label, key in (
            ("첨부파일", "attachments"),
            ("본문 링크", "attached_links"),
            ("이미지", "attached_images"),
        ):
            values = item.get(key) or []
            if values:
                resources.append(f"{label}: " + ", ".join(values[:3]))

        sections.append(
            """제목: {title}
날짜: {date}
카테고리: {category}
출처: {source}
URL: {url}
notice_id: {notice_id}
chunk_id: {chunk_id}
{resources}
본문:
{chunk_text}""".format(
                title=item["title"],
                date=item["date"],
                category=item["category"],
                source=item["source"],
                url=item["url"] or "(URL 없음)",
                notice_id=item["notice_id"],
                chunk_id=item["chunk_id"],
                resources="\n".join(resources),
                chunk_text=snippet.strip(),
            ).strip()
        )

    return "\n\n---\n\n".join(sections)


def generate_answer(query: str, context: str) -> str:
    """Generate a prompt template for Gemma 4 or another downstream LLM."""
    if not context.strip():
        return NO_RELEVANT_NOTICE_MESSAGE

    prompt = f"""아래 공지사항 정보를 바탕으로 사용자 질문에 답변하세요.

STRICT MODE:
- 검색 결과 정보에 명시된 내용만 사용하세요.
- 검색 결과 외 사실, 일정, 링크, 신청 방법을 추측하거나 보완하지 마세요.
- 모든 공지 요약에는 반드시 출처 URL을 포함하세요.
- URL이 "(URL 없음)"이면 출처가 불완전하다고 말하고 링크를 만들지 마세요.
- 질문과 직접 관련 없는 검색 결과는 답변에서 제외하세요.
- 불확실하거나 검색 결과에서 확인되지 않는 내용은 모른다고 답변하세요.
- 검색 결과가 비어 있거나 관련성이 낮으면 "{NO_RELEVANT_NOTICE_MESSAGE}"라고만 답변하세요.

사용자 질문: {query}

검색 결과 정보:
{context}

요청:
- 답변에는 공지 제목, 날짜, 핵심 내용, URL을 포함하세요.
- 첨부파일이나 신청 링크가 있으면 함께 안내하세요.
- 검색 결과에 없는 내용은 추측하지 마세요.
- 불확실하면 모른다고 답변하세요.
- 관련 내용이 없으면 "관련 공지가 없습니다."라고 답변하세요.
"""
    return prompt


def search_quality_guidelines() -> List[str]:
    """Return a checklist for manual search quality inspection."""
    return [
        "질문의 의도와 검색 결과의 category가 일치하는가?",
        "시간 표현(최근, 작년, 지난 학기, 2025년)이 metadata filter로 반영되는가?",
        "동일 공지 chunk가 top-k를 과도하게 점유하지 않는가?",
        "이전/다음 chunk 확장 context가 답변에 필요한 주변 정보를 보강하는가?",
        "BM25 키워드 매칭과 vector semantic search가 함께 후보를 만드는가?",
        "reranking을 켰을 때 최종 순위가 질문-본문 관련성 기준으로 재정렬되는가?",
        "url, attachments, attached_links, attached_images metadata가 정상 출력되는가?",
    ]
