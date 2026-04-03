# Kookmin University CS/SW Notice Scraper

국민대학교 소프트웨어융합대학(CS) 및 SW중심대학사업단(SW)의 공지사항을 수집하는 크롤링 도구입니다.

---

## 주요 기능

* **멀티 소스 수집**: 소프트웨어융합대학 및 SW중심대학사업단의 개별 게시판 데이터 통합.
* **증분 수집**: `kookmin_notices.json` 파일을 참조하여 중복된 URL은 건너뛰고 신규 게시글만 수집.
* **상세 데이터 추출**: 제목, 날짜, 본문 텍스트 외에도 첨부파일 링크, 본문 내 하이퍼링크, 이미지 주소를 별도로 추출.
* **데이터 정제**: 본문 내 불필요한 개행 및 특수 공백을 정규표현식으로 전처리.

---

## 파일 구조

| 파일명 | 역할 |
| :--- | :--- |
| `main.py` | 프로그램 실행 엔트리 포인트. 데이터 로드, 중복 체크 및 전체 크롤링 프로세스 제어. |
| `cs_scraper.py` | 소프트웨어융합대학 홈페이지(`cs.kookmin.ac.kr`) 전용 스크래퍼 클래스. |
| `sw_scraper.py` | SW중심대학사업단 홈페이지(`software.kookmin.ac.kr`) 전용 스크래퍼 클래스. |
| `config.py` | 수집 대상 URL 리스트, 카테고리 설정, 최대 페이지 수(`MAX_PAGES`) 등 환경 설정. |
| `kookmin_notices.json` | 최종 수집 데이터가 저장되는 JSON 파일. |

---

## 설치 및 실행

### 요구 사항
* Python 3.x
* BeautifulSoup4
* Requests

### 실행 방법
1. 의존성 설치:
   ```bash
   pip install beautifulsoup4 requests
   ```
2. 크롤러 실행:
   ```bash
   python main.py
   ```

---

## 향후 업데이트 계획

* **Logger 통합**: 현재 `print()`로 처리된 표준 출력을 `logger.py` 모듈로 교체 예정.
* **서버 자동화**: 백그라운드 실행 및 주기적 수집을 위한 로그 파일(.log) 기록 기능 추가.
* **에러 핸들링**: 네트워크 타임아웃 및 예외 상황에 대한 재시도 로직 강화.
