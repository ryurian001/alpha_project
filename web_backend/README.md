# Web Backend

이 디렉토리는 국민대학교(KMU) 챗봇의 백엔드 서비스를 담당합니다. Python과 FastAPI를 기반으로 작성되었습니다.

## 기술 스택
- Python 3.x
- FastAPI
- Uvicorn
- Pydantic

## 설치 및 실행 방법

1. 의존성 설치:
```bash
pip install -r requirements.txt
```

2. 서버 실행:
```bash
uvicorn main:app --reload
```
서버는 기본적으로 `http://localhost:8000`에서 실행됩니다.

## 디렉토리 구조
- `main.py`: FastAPI 앱 설정 및 라우터 엔드포인트 정의
- `schemas.py`: Pydantic을 이용한 Request / Response 데이터 모델 정의
- `services/`: 비즈니스 로직(채팅 생성 등) 처리. 현재는 `mock_rag.py`를 통해 임시 응답을 반환합니다.

## 추후 API 연동 가이드

프론트엔드 등 클라이언트에서 백엔드 API와 연동하는 방법은 다음과 같습니다.

### 1. Health Check
서버의 구동 상태를 확인합니다.
- **URL:** `GET /`
- **Response:**
  ```json
  {
    "status": "ok"
  }
  ```

### 2. 채팅 요청 (Chat API)
사용자의 질문을 서버로 전송하고, RAG(검색 증강 생성) 기반의 응답과 참고 문헌을 반환받습니다.
- **URL:** `POST /chat`
- **Headers:** `Content-Type: application/json`
- **Request Body (JSON):**
  ```json
  {
    "question": "질문 내용을 입력하세요."
  }
  ```
- **Response Body (JSON):**
  ```json
  {
    "answer": "AI가 생성한 답변입니다.",
    "references": [
      {
        "title": "참고 공지사항 제목",
        "content": "참고한 공지사항의 일부 내용..."
      }
    ]
  }
  ```

> **API 연동 팁 (프론트엔드 개발자용)**
> - 로컬 개발 시에는 CORS 설정이 이미 허용(`allow_origins=["*"]`)되어 있으므로 `http://localhost:8000/chat` 으로 바로 POST 요청을 보내면 됩니다.
> - 추후 실제 DB(Vector DB)나 LLM이 연결되면 응답 생성 시 지연(Latency)이 발생할 수 있으므로, 프론트엔드 연동 시 로딩 스피너 등의 비동기 처리 UI를 권장합니다.