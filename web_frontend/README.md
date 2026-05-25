# Web Frontend

이 디렉토리는 국민대학교(KMU) 챗봇의 웹 프론트엔드 UI를 담당합니다. React와 Vite를 사용하여 빠르고 가벼운 개발 환경을 제공합니다.

## 기술 스택
- React (18+)
- Vite
- Vanilla CSS (`styles/main.css`)

## 설치 및 실행 방법

1. 패키지 설치:
```bash
npm install
```

2. 개발 서버 실행:
```bash
npm run dev
```
개발 서버는 기본적으로 `http://localhost:5173` (Vite 기본 포트) 등에서 실행됩니다. 터미널에 표시된 로컬 주소로 접속하세요.

## 환경 변수 설정
백엔드 API 주소를 변경하려면 `web_frontend` 폴더 최상단에 `.env` 파일을 생성하고 아래와 같이 설정합니다.
```env
VITE_API_BASE_URL=http://localhost:8000
```
*(기본값은 `http://localhost:8000`으로 설정되어 있습니다.)*

## 주요 파일 구조 및 설명
- `src/App.jsx`: 애플리케이션의 메인 컴포넌트
- `src/api/chatApi.js`: 백엔드 API(`POST /chat`)와 통신하는 함수.
  - 현재 로컬 테스트의 편의를 위해 `test1`, `test2`, `test3` 등의 키워드를 입력하면, 프론트엔드 단에서 작성된 목업(Mock) 데이터와 약간의 딜레이(Delay)를 응답하도록 설정되어 있습니다.
- `src/components/`:
  - `ChatBox.jsx`: 채팅 UI 영역을 감싸는 메인 컨테이너 레이아웃
  - `MessageList.jsx`: 질문과 답변이 오고가는 대화 스크롤 리스트
  - `MessageInput.jsx`: 사용자 질문을 입력하고 전송하는 인풋 폼
- `src/hooks/useChat.js`: 채팅 기록, 로딩 상태 등 전반적인 상태를 관리하는 커스텀 훅
- `src/styles/main.css`: 애플리케이션 스타일 속성 정의