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
- [x] 경쟁 프로젝트 내부 기능 재확인 (`docs/research.md` §1) · mem0, Hindsight, cognee, graphiti, basic-memory, mnemo, kibisis, world-model-mcp
- [x] 설계안 작성: 목적·차별점·위협 모델·구조·사용성 (`docs/design.md`)
- [x] 규칙에 문서 경로 표 추가 (`AGENTS.md` Project Documents)
- [x] 설계 독립 재검토 1차 반영 (`docs/decisions.md` 재검토 반영)
- [x] 설계 2차 일관성 검토 반영 (`docs/design.md` 3판)
- [x] 구현 전 체크포인트: 저장·서명·MCP·화면 기술 선택 (`docs/design.md` §12) · mcp, cryptography, webauthn, starlette, kiwipiepy, sqlite-vec

## S0 개발 환경

- [x] pyproject와 uv 해시 고정 lock, exclude-newer 설정 · uv
- [x] gitleaks pre-commit 훅 · gitleaks
- [x] 시작 훅 검사 이식 · gon-nexus startup_hooks.py

## S1 기록 계층 (`docs/design.md` §6, §7)

- [x] RFC 6962 Merkle 루트 계산과 공인 벡터 시험 · transparency-dev/merkle, hypothesis
- [x] 데이터 형식 규격 1차 (`docs/format.md`: 항목·엄격 판독·genesis·체크포인트) · c2sp.org/tlog-checkpoint
- [x] init(복구 키·genesis)·추가 전용 로그·내용 분리 저장 · sqlite3, cryptography
- [x] 전체·증분 재생 검증 상태와 verify CLI · typer
- [x] 변조 시나리오 시험(해시 체인 기준선 대비) + 변이 시험 · pytest
- [x] 여러 프로세스 동시 쓰기 시험 (`docs/decisions.md` V3)
- [x] 재생 비용 측정 1만·10만 건 (`docs/measurements/`)

## S2 MCP 서버 (D3·D8 대기)

- [ ] remember·recall·forget 도구, 텍스트 꼬리표·무작위 구획, 상태 리소스 · mcp
- [ ] 한국어 어휘 검색 1단계 (2-gram·형태소 비교) · kiwipiepy
- [ ] 실제 MCP 클라이언트 2종 연결 시험 (V4)
- [ ] 종단 공격 측정 하네스와 기준선 (D8)
- [ ] macOS 커밋 내구성 fullfsync 측정 (V10)

## S3~S6 신뢰 (D2·D7 대기)

- [ ] S3 암호 키 파일(Argon2id)·승인문 서명·변경 서명·등급 세 축 · cryptography
- [ ] S4 외부 증인 기록·대조 (V6)
- [ ] S5 키 권한·철회·복구 키 서명
- [ ] S6 gonlith taint·gate 명령과 Claude Code 훅 예시 (V8, V9)

## S7 이후

- [ ] S7 웹 화면 상태·승인함·감사 (V7) · starlette, uvicorn
- [ ] S8 패스키 승인 (V1) · webauthn
- [ ] S9 setup 마법사·doctor·기존 기억 가져오기 (V4)
- [ ] S10 한국어 검색 평가셋·측정, 선택적 임베딩 · fastembed, model2vec, sqlite-vec
- [ ] S11 시점 질의·충돌 후보
- [ ] S12 진짜 삭제
- [ ] S13 내보내기와 별도 검증기 (포함·일관성 증명)
- [ ] 공개 체크리스트: PyPI·MCPB·README·호환표 (D5 이후, V5)

## 사용자 확인

- [ ] 회사 겸업·직무발명 규정 확인 (`docs/decisions.md` D5)
- [ ] 결정 D1~D4, D6~D8 답변 (`docs/decisions.md`)
