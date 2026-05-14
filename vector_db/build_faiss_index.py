from __future__ import annotations

import argparse
import json
import logging
import pickle
import time
from pathlib import Path
from typing import Any

import numpy as np

try:
    import faiss
except ImportError as exc:
    raise ImportError("Install faiss-cpu before rebuilding the index.") from exc

try:
    from sentence_transformers import SentenceTransformer
except ImportError as exc:
    raise ImportError("Install sentence-transformers before rebuilding the index.") from exc

from faiss_retriever import DEFAULT_EMBEDDING_MODEL

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHUNKS = PROJECT_ROOT / "data" / "chunks" / "notices_chunks.jsonl"
DEFAULT_INDEX = PROJECT_ROOT / "vector_db" / "kmu_notice_index.faiss"
DEFAULT_STORE = PROJECT_ROOT / "vector_db" / "kmu_notice_store.pkl"

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a FAISS index from notice chunks.")
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS)
    parser.add_argument("--index-output", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--store-output", type=Path, default=DEFAULT_STORE)
    parser.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    parser.add_argument("--metric", choices=["l2", "ip"], default="l2")
    parser.add_argument("--normalize", action="store_true")
    return parser.parse_args()


def load_chunks(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def build_index(args: argparse.Namespace) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    started_at = time.perf_counter()
    rows = load_chunks(args.chunks)
    if not rows:
        raise ValueError(f"No chunks found: {args.chunks}")

    documents = [row["text"] for row in rows]
    metadatas = []
    ids = []
    for row in rows:
        metadata = dict(row.get("metadata") or {})
        metadata.setdefault("notice_id", row.get("notice_id", ""))
        metadata.setdefault("chunk_index", row.get("chunk_index", 0))
        metadata.setdefault("chunk_id", row.get("chunk_id", ""))
        metadatas.append(metadata)
        ids.append(row.get("chunk_id", metadata.get("chunk_id", "")))

    model = SentenceTransformer(args.embedding_model)
    embeddings = model.encode(documents, convert_to_numpy=True, show_progress_bar=True)
    embeddings = np.asarray(embeddings, dtype=np.float32)
    if args.normalize:
        faiss.normalize_L2(embeddings)

    if args.metric == "ip":
        index = faiss.IndexFlatIP(embeddings.shape[1])
    else:
        index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)

    args.index_output.parent.mkdir(parents=True, exist_ok=True)
    args.store_output.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(args.index_output))

    store = {
        "ids": ids,
        "documents": documents,
        "embedding_docs": documents,
        "metadatas": metadatas,
        "bm25_corpus": documents,
        "embedding_model": args.embedding_model,
        "metric": args.metric,
        "normalized": args.normalize,
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    with args.store_output.open("wb") as file:
        pickle.dump(store, file)

    logger.info(
        "index_rebuild.completed chunks=%d dim=%d latency_ms=%.2f index=%s store=%s",
        len(rows),
        embeddings.shape[1],
        (time.perf_counter() - started_at) * 1000,
        args.index_output,
        args.store_output,
    )


if __name__ == "__main__":
    build_index(parse_args())
