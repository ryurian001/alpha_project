def mock_answer(question: str):
    return {
        "answer": f"'{question}'에 대한 임시 답변입니다. 현재는 모델 연결 전 Mock API 상태입니다.",
        "references": [
            {
                "title": "임시 공지 문서",
                "content": "DLPC 환경 준비 후 실제 FAISS 검색 결과가 여기에 들어갈 예정입니다."
            }
        ]
    }