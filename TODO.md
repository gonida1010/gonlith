# 할 일 목록 (gonlith)

> **규칙**
> - 한 건 = 체크박스 한 줄. 할 일은 `- [ ]`, 끝나면 `- [x]`로 바꾼다.
> - 설명은 한 줄. 줄바꿈·하위 설명·첨부 금지.
> - **이 파일은 절대 기록(로그) 파일이 아니다.** 날짜·결과·수치·경과·회고는 쓰지 않는다. 그런 내용은 설계 문서나 산출물에 남긴다.
> - 용도: AI 세션이 바뀌거나 다른 AI와 함께 구현할 때 **어디까지 했는지** 확인하는 용도.
> - 위에서 아래로 진행 순서다. **처음 나오는 `- [ ]`이 지금 이어서 할 항목이다.** 단, 맨 아래 "사용자 확인" 절은 사용자 몫이라 순서에서 제외한다.
> - 새 세션은 작업 시작 전에 이 파일부터 읽고, 항목을 끝낼 때마다 바로 체크한다.
> - 쓴(또는 쓰기로 정한) 도구·스킬·오픈소스는 줄 끝 `·` 뒤에 이름이나 링크만 적는다. 설명은 쓰지 않는다.
> - 설계 `docs/design.md`, 근거 `docs/research.md`, 결정 `docs/decisions.md`. "(D숫자 대기)" 항목은 `docs/decisions.md`의 사용자 결정 전에는 시작하지 않는다.

## 준비

- [x] 이름(Gonlith)·라이선스(Apache-2.0)·공개 저장소 생성 · GitHub
- [x] 저장소 받기, 프로젝트 규칙(AGENTS·CLAUDE·GEMINI)과 할 일 목록 추가
- [x] 경쟁 프로젝트 내부 기능 재확인 (`docs/research.md` §1, §7) · mem0, Hindsight, cognee, graphiti, basic-memory, mcp-memory-service
- [x] 설계 3판(보안 중심) 작성·재검토 2회, 보호 모드 초안으로 보관 (`docs/protection-mode.md`)
- [x] 설계 4판: 편한 범용 기억·지식 저장소 + 쉬운 관리 중심으로 전환 (`docs/design.md`)
- [x] 규칙에 문서 경로 표 추가 (`AGENTS.md` Project Documents)
- [x] 구현 전 체크포인트: 저장·MCP·화면·수집 기술 선택 (`docs/design.md` §15) · mcp, markitdown, pypdf, trafilatura, watchfiles, kiwipiepy

## S0 개발 환경

- [x] pyproject와 uv 해시 고정 lock, exclude-newer 설정 · uv
- [x] gitleaks pre-commit 훅 · gitleaks
- [x] 시작 훅 검사 이식 · gon-nexus startup_hooks.py

## S1 기록 계층 (`docs/design.md` §13)

- [x] RFC 6962 Merkle 루트 계산과 공인 벡터 시험 · transparency-dev/merkle, hypothesis
- [x] 데이터 형식 규격 1차 (`docs/format.md`)
- [x] genesis·추가 전용 로그·내용 분리 저장 · sqlite3
- [x] 전체·증분 재생 검증과 verify CLI · typer
- [x] 변조 시나리오 시험 + 변이 시험
- [x] 여러 프로세스 동시 쓰기 시험 (V3)
- [x] 재생 비용 측정 (`docs/measurements/s1-record-layer.md`)
- [x] genesis 키 선택화(4판), 복구 키 출력 제거

## S2 MCP 핵심 (`docs/design.md` §11)

- [x] 첫 실행 자동 init과 serve 명령 · mcp
- [x] remember·search·forget 도구, 텍스트 결과·출처 꼬리표·외부 내용 무작위 구획
- [x] 한국어 어휘 검색 1단계 (2-gram·형태소 비교, `docs/measurements/s2-mcp-core.md`) · kiwipiepy
- [x] 로컬 모델(Ollama) MCP 하네스로 교차 기억 시험 (`scripts/local_agent_eval.py`) · ollama, mcp
- [ ] 로컬 하네스 반복 실행(성공률)과 서버 안내문 개선 비교 (저장 언어·재검색 권장)
- [x] 외부 평가셋 내려받기 스크립트와 캐시 (`eval/datasets.toml`, `scripts/fetch_eval_datasets.py`)
- [x] macOS 커밋 내구성 fullfsync 측정 (V10)

## S3~S6 관리·연결·수집

- [ ] S3 관리 화면 1차: 검색·보기·편집·휴지통·이력·되돌리기·AI가 아는 나 · starlette, uvicorn
- [ ] S3a Markdown 거울 폴더 (`docs/design.md` §7.4)
- [ ] S4 setup 마법사·doctor·클라이언트 자동 연결 (V4)
- [ ] S5 문서 수집 1차: 끌어다 놓기·add·ingest, md/txt/pdf/docx/웹 (V11) · markitdown, pypdf, trafilatura
- [ ] S5b 음성·대본 수집: 대본 파일 가져오기(필수), 녹음 파일 음성 인식(선택 설치, CER 통과 시) · whisper.cpp, silero-vad, sherpa-onnx
- [ ] S6 감시 폴더·재수집·백그라운드 담당 · watchfiles

## S7 이후

- [ ] S7 한국어·하이브리드 검색 측정, 임베딩 선택 (D6) · fastembed, model2vec, sqlite-vec
- [ ] S8 정리 제안 사람 처리: 중복·충돌·오래됨·미분류
- [ ] S9 정리 AI 처리자(로컬·연결된 AI), 자동 적용, 일괄 되돌리기 (V12)
- [ ] S10 공간 공개 범위, 기존 기억 가져오기
- [ ] S11 진짜 삭제·내보내기
- [ ] S12 보호 모드 (선택, `docs/protection-mode.md`) · cryptography, webauthn
- [ ] 릴리스 체크리스트: PyPI·MCPB·설치 스크립트·README·호환표·형식 판 1 고정 (D4, V5)

## 사용자 확인

- [x] 회사 겸업·직무발명 규정 확인 (`docs/decisions.md` D5, 사용자 판단으로 종료)
- [x] 결정 D10, D11 답변
- [x] 결정 D4 첫 릴리스 범위 답변 (`docs/decisions.md`)
- [x] 결정 D12 음성 수집 첫 릴리스 포함 여부 (`docs/decisions.md`)
