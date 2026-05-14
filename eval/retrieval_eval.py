from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import mean
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VECTOR_DB = PROJECT_ROOT / "vector_db"
if str(VECTOR_DB) not in sys.path:
    sys.path.append(str(VECTOR_DB))

from faiss_retriever import build_context, generate_answer, retrieve

DEFAULT_BENCHMARK = PROJECT_ROOT / "eval" / "benchmark_qa.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate notice retrieval quality.")
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--rerank", action="store_true")
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def is_relevant(item: dict[str, Any], expected: dict[str, Any]) -> bool:
    notice_ids = set(expected.get("relevant_notice_ids") or [])
    categories = set(expected.get("relevant_categories") or [])

    if notice_ids and item.get("notice_id") in notice_ids:
        return True
    if categories and item.get("category") in categories:
        return True
    return False


def score_query(expected: dict[str, Any], results: list[dict[str, Any]], top_k: int) -> dict[str, float]:
    hits = [1 if is_relevant(item, expected) else 0 for item in results[:top_k]]
    relevant_count = sum(hits)
    has_known_notice_labels = bool(expected.get("relevant_notice_ids"))
    denominator = len(expected["relevant_notice_ids"]) if has_known_notice_labels else 1
    reciprocal_rank = 0.0
    for index, hit in enumerate(hits, start=1):
        if hit:
            reciprocal_rank = 1.0 / index
            break

    return {
        "recall": min(relevant_count / max(denominator, 1), 1.0),
        "precision": relevant_count / top_k,
        "mrr": reciprocal_rank,
    }


def evaluate_end_to_end(expected: dict[str, Any], prompt_or_answer: str) -> dict[str, float]:
    required = expected.get("answer_contains") or []
    if not required:
        return {"answer_keyword_hit": 1.0}
    hits = sum(1 for keyword in required if keyword in prompt_or_answer)
    return {"answer_keyword_hit": hits / len(required)}


def main() -> None:
    args = parse_args()
    rows = load_jsonl(args.benchmark)
    per_query = []

    for row in rows:
        results = retrieve(row["question"], top_k=args.top_k, enable_rerank=args.rerank)
        metrics = score_query(row, results, args.top_k)
        context = build_context(results)
        prompt = generate_answer(row["question"], context)
        e2e = evaluate_end_to_end(row, prompt)
        per_query.append({**row, **metrics, **e2e, "result_count": len(results)})

    summary = {
        "queries": len(per_query),
        "recall@k": mean(item["recall"] for item in per_query) if per_query else 0.0,
        "precision@k": mean(item["precision"] for item in per_query) if per_query else 0.0,
        "mrr": mean(item["mrr"] for item in per_query) if per_query else 0.0,
        "answer_keyword_hit": mean(item["answer_keyword_hit"] for item in per_query) if per_query else 0.0,
    }

    print(json.dumps({"summary": summary, "per_query": per_query}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
