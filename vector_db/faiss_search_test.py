from __future__ import annotations

import sys
from pathlib import Path
from textwrap import shorten

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from faiss_retriever import build_context, generate_answer, retrieve, search_quality_guidelines


TEST_QUERIES = [
    "최근 장학공지 알려줘",
    "소프트웨어융합대학 특강 공지 찾아줘",
    "취업 관련 공지 뭐 있어?",
    "SW중심대학사업단 학생지원 프로그램 알려줘",
    "2025년 장학금 관련 공지 찾아줘",
]


def print_result_item(item: dict) -> None:
    score_line = (
        f"hybrid={item['hybrid_score']:.4f} "
        f"vector={item['vector_score']:.4f} "
        f"bm25={item['bm25_score']:.4f}"
    )
    if item.get("rerank_score") is not None:
        score_line += f" rerank={item['rerank_score']:.4f}"
    print(f"rank={item['rank']} | {score_line} | title={item['title']}")
    print(
        f"  date={item['date']} | category={item['category']} | "
        f"notice_id={item['notice_id']} | chunk={item['chunk_index']} | url={item['url']}"
    )
    snippet = item['chunk_text'].replace('\n', ' ')
    print(f"  chunk_text={shorten(snippet, width=250, placeholder='...')}")
    print()


def run_search_tests(top_k: int = 5) -> None:
    print("=== FAISS 검색 품질 테스트 ===")
    print("쿼리 목록:")
    for query in TEST_QUERIES:
        print(f"- {query}")
    print()

    for query in TEST_QUERIES:
        print(f"---\n검색 질의: {query}\n")
        try:
            results = retrieve(query, top_k=top_k)
        except Exception as exc:
            print(f"검색 오류: {exc}")
            continue

        if not results:
            print("검색 결과가 없습니다. index, store 파일 또는 임베딩 모델을 확인하세요.")
            continue

        for item in results:
            print_result_item(item)

        print("검색 품질 점검 기준:")
        for check in search_quality_guidelines():
            print(f"- {check}")

        context = build_context(results)
        prompt = generate_answer(query, context)
        print("\n[LLM 전달용 Prompt 예시]")
        print(prompt)
        print("\n")


if __name__ == "__main__":
    run_search_tests(top_k=5)
