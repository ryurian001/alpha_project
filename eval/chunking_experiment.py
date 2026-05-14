from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from statistics import mean
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CLEAN = PROJECT_ROOT / "data" / "clean" / "notices_clean.jsonl"
DEFAULT_BENCHMARK = PROJECT_ROOT / "eval" / "benchmark_qa.jsonl"

TOKEN_RE = re.compile(r"[가-힣A-Za-z0-9]+")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run lightweight chunking strategy retrieval experiments.")
    parser.add_argument("--clean", type=Path, default=DEFAULT_CLEAN)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--top-k", type=int, default=5)
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def tokenize(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(text or "")}


def build_document(notice: dict[str, Any]) -> str:
    return "\n".join(
        part
        for part in [
            f"제목: {notice.get('title', '')}",
            f"출처: {notice.get('source', '')}",
            f"분류: {notice.get('category', '')}",
            f"날짜: {notice.get('date', '')}",
            notice.get("content", ""),
        ]
        if part
    )


def fixed_chunks(text: str, size: int, overlap: int) -> list[str]:
    if len(text) <= size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + size])
        start += max(size - overlap, 1)
    return chunks


def recursive_chunks(text: str, size: int = 900, overlap: int = 120) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n{2,}", text) if part.strip()]
    chunks = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= size:
            current = candidate
        else:
            if current:
                chunks.append(current)
            chunks.extend(fixed_chunks(paragraph, size, overlap) if len(paragraph) > size else [paragraph])
            current = ""
    if current:
        chunks.append(current)
    return chunks


def semantic_chunks(text: str, size: int = 900) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    chunks = []
    current = []
    current_tokens: set[str] = set()
    for line in lines:
        line_tokens = tokenize(line)
        overlap = len(current_tokens & line_tokens) / max(len(line_tokens), 1)
        candidate = "\n".join(current + [line])
        if current and (len(candidate) > size or overlap < 0.08):
            chunks.append("\n".join(current))
            current = [line]
            current_tokens = set(line_tokens)
        else:
            current.append(line)
            current_tokens |= line_tokens
    if current:
        chunks.append("\n".join(current))
    return chunks


def build_chunks(notices: list[dict[str, Any]], strategy: str) -> list[dict[str, Any]]:
    strategies: dict[str, Callable[[str], list[str]]] = {
        "smaller": lambda text: fixed_chunks(text, 500, 80),
        "baseline": lambda text: fixed_chunks(text, 900, 120),
        "larger": lambda text: fixed_chunks(text, 1400, 180),
        "recursive": recursive_chunks,
        "semantic": semantic_chunks,
    }
    chunker = strategies[strategy]
    rows = []
    for notice in notices:
        for index, text in enumerate(chunker(build_document(notice))):
            rows.append(
                {
                    "notice_id": notice["id"],
                    "chunk_index": index,
                    "category": notice.get("category", ""),
                    "title": notice.get("title", ""),
                    "text": text,
                    "tokens": tokenize(text),
                }
            )
    return rows


def score_chunks(query: str, chunks: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
    query_tokens = tokenize(query)
    scored = []
    for chunk in chunks:
        lexical = len(query_tokens & chunk["tokens"]) / max(len(query_tokens), 1)
        category_bonus = 0.25 if chunk["category"] in query else 0.0
        scored.append((lexical + category_bonus, chunk))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for score, chunk in scored[:top_k] if score > 0]


def is_relevant(chunk: dict[str, Any], expected: dict[str, Any]) -> bool:
    notice_ids = set(expected.get("relevant_notice_ids") or [])
    categories = set(expected.get("relevant_categories") or [])
    return (notice_ids and chunk["notice_id"] in notice_ids) or (categories and chunk["category"] in categories)


def metrics_for(rows: list[dict[str, Any]], chunks: list[dict[str, Any]], top_k: int) -> dict[str, float]:
    recall_values = []
    precision_values = []
    mrr_values = []
    for row in rows:
        results = score_chunks(row["question"], chunks, top_k)
        hits = [1 if is_relevant(chunk, row) else 0 for chunk in results]
        precision_values.append(sum(hits) / top_k)
        recall_values.append(1.0 if any(hits) else 0.0)
        reciprocal_rank = 0.0
        for index, hit in enumerate(hits, start=1):
            if hit:
                reciprocal_rank = 1.0 / index
                break
        mrr_values.append(reciprocal_rank)
    return {
        "recall@k": mean(recall_values) if recall_values else 0.0,
        "precision@k": mean(precision_values) if precision_values else 0.0,
        "mrr": mean(mrr_values) if mrr_values else 0.0,
    }


def main() -> None:
    args = parse_args()
    notices = load_jsonl(args.clean)
    benchmark = load_jsonl(args.benchmark)
    results = {}
    for strategy in ["smaller", "baseline", "larger", "recursive", "semantic"]:
        chunks = build_chunks(notices, strategy)
        metrics = metrics_for(benchmark, chunks, args.top_k)
        results[strategy] = {**metrics, "chunks": len(chunks)}

    best = max(results.items(), key=lambda item: (item[1]["mrr"], item[1]["recall@k"], item[1]["precision@k"]))
    print(json.dumps({"best_strategy": best[0], "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
