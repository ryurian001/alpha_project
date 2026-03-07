# 교내 챗봇 개발 프로젝트 (Kookmin Chatbot)
> [cite_start]**국민대학교 학사 및 행정 정보 제공을 위한 RAG 기반 지능형 챗봇 시스템** [cite: 25]

[cite_start]본 프로젝트는 학생들이 파편화된 교내 정보를 쉽고 빠르게 확인할 수 있도록 **RAG(검색 증강 생성)** 기술과 **LORA 경량 파인튜닝**을 결합한 실시간 문서 기반 지능형 챗봇을 설계 및 구현하는 것을 목표로 합니다. [cite: 25, 35, 42]

---

## 팀원
[cite_start]**소프트웨어융합대학** 인공지능학부 및 소프트웨어학부 학생 7명으로 구성된 프로젝트 팀입니다. [cite: 18, 276]

| 구분 | 성명 | 학과/전공 | 학번 | 주요 역할 (Role) |
| :--- | :--- | :--- | :--- | :--- |
| **팀장** | **오현제** | 인공지능학부 | 20243161 | [cite_start]스터디 리드, RAG 고도화 및 기술 보고서 총괄 [cite: 175] |
| **팀원** | **이승찬** | 인공지능학부 | 20223190 | [cite_start]데이터 정제 파이프라인 및 양자화 모델 성능 측정 [cite: 189] |
| **팀원** | **이상현** | 인공지능학부 | 20223187 | [cite_start]BGE 모델 실험 및 Vector DB 메타데이터 설계 [cite: 204] |
| **팀원** | **유리안** | 인공지능학부 | 20220367 | [cite_start]LORA 하이퍼파라미터 튜닝 및 환각 탐지 기준 수립 [cite: 219] |
| **팀원** | **이승빈** | 인공지능학부 | 20223189 | [cite_start]추론 엔진 최적화 및 양자화 모델 서빙 튜닝 [cite: 234] |
| **팀원** | **이종민** | 인공지능학부 | 20223194 | [cite_start]백엔드 API 호출 구조 설계 및 챗봇 UI 레이아웃 구현 [cite: 249] |
| **팀원** | **이동규** | 소프트웨어학부 | 20223112 | [cite_start]반응형 웹 스타일링 및 사용자 관점 UX 개선 제안 [cite: 265] |

---

## 주요 기술 스택
* [cite_start]**Core Engine**: RAG (Retrieval-Augmented Generation) [cite: 35]
* [cite_start]**Optimization**: LoRA (Low-Rank Adaptation) 파인튜닝 [cite: 42][cite_start], INT8/INT4 Quantization (양자화) [cite: 59, 111]
* [cite_start]**Database**: Vector Database (Chroma, FAISS 등) [cite: 175, 189]
* [cite_start]**Data Pipeline**: Python 기반 웹 크롤링 및 전처리 [cite: 38, 53]
* [cite_start]**Interface**: Web-based User/Admin Dashboard [cite: 62, 63]

---

## 프로젝트 핵심 목표
1.  [cite_start]**실시간 정보 반영**: 국민대학교 홈페이지를 주기적으로 크롤링하여 최신 학사 공지를 자동으로 수집 및 갱신합니다. [cite: 53]
2.  [cite_start]**환각(Hallucination) 방지**: 단순 FAQ 방식이 아닌, 공식 문서 근거를 바탕으로 답변을 생성하며 출처를 명시합니다. [cite: 34, 37, 86]
3.  [cite_start]**리소스 최적화**: 양자화 기법을 통해 제한된 GPU 환경에서도 원활한 실시간 응답이 가능하도록 구현합니다. [cite: 42, 60]
4.  [cite_start]**신뢰성 확보**: 가드레일 학습을 통해 근거가 불충분한 질문에는 무리하게 답변하지 않도록 설계합니다. [cite: 43, 107]

---

## 활동 안내
* [cite_start]**활동 기간**: 2026. 03. 02. ~ 2026. 06. 19. (15주 과정) [cite: 2, 9]
* [cite_start]**지도 교수**: 소프트웨어융합대학 이현기 교수님 [cite: 2, 289]
* [cite_start]**교과목**: 알파프로젝트 I (9학점) [cite: 2]

---
[cite_start]*본 프로젝트는 대학혁신지원사업의 일환으로 진행됩니다.* [cite: 15]
