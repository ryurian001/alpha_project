# Notice Preprocessing

크롤러가 만든 `kookmin_notices.json`을 챗봇/RAG에서 쓰기 좋은 형태로 정리합니다.

## 입력 파일 위치

아래 위치 중 하나에 `kookmin_notices.json`을 두면 자동으로 찾습니다.

```text
data/raw/kookmin_notices.json
crawler/movinggyu/kookmin_notices.json
kookmin_notices.json
```

다른 위치에 있다면 `--input`으로 직접 지정하면 됩니다.

## 실행

```bash
python preprocess/preprocess_notices.py
```

다른 경로의 파일을 전처리하려면:

```bash
python preprocess/preprocess_notices.py --input data/raw/kookmin_notices.json
```

## 출력 파일

```text
data/clean/notices_clean.jsonl
data/chunks/notices_chunks.jsonl
```

- `notices_clean.jsonl`: 공지 1개당 1줄로 정리된 데이터
- `notices_chunks.jsonl`: 긴 공지를 검색하기 좋은 작은 조각으로 나눈 데이터

## 전처리 내용

- 제목, 날짜, 본문, URL, 분류, 출처를 정리합니다.
- 본문 안의 불필요한 공백, 빈 줄, 보이지 않는 문자를 줄입니다.
- 본문에 섞인 URL은 제거하고, 첨부파일/링크/이미지 목록은 URL을 유지한 채 중복 제거합니다.
- 첨부파일/링크/이미지 목록은 chunk 본문과 metadata에도 포함합니다.
- `javascript:`, `mailto:`, `tel:`, `data:`처럼 챗봇 답변에 직접 연결하기 어려운 값은 제외합니다.
- 같은 URL의 공지는 하나만 남깁니다.
- 각 공지를 일정 길이의 chunk로 나눠 벡터 DB에 넣기 쉬운 형태로 만듭니다.
