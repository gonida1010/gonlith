# Gonlith 근거 조사

> 설계 정본: [`docs/design.md`](design.md). 이 문서는 설계 판단의 근거(출처·버전·날짜)만 모은다.
> 조사일 2026-11-20. **확인** = 코드·문서·1차 출처 대조, **추정** = 추론. 논문·프로젝트 수치는 각자의 보고값이며 우리 측정이 아니다. 별 개수는 GitHub API 당일 값이며 품질 지표가 아니다.

## 1. 경쟁 프로젝트 내부 확인

각 저장소를 얕게 복제해 코드에서 확인했다. 경로는 각 저장소 기준.

| 프로젝트 (릴리스 / 마지막 커밋) | 저장 방식 | 무결성 장치 | 시간 모델 | 오염 방어 | 한국어 | MCP |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| mem0 (2.2.1, 2026-09-25 / 11-18) | 고칠 수 있는 벡터 행. `update`·`delete`가 덮어씀 (`mem0/memory/main.py`) | `history` 테이블(변경 전후 값). `hash`는 중복 제거용 MD5. 체인·서명 없음 | 유효기간 없음 | 핵심에 없음 | spaCy 영어 모델, 기본 임베딩 OpenAI | 호스팅 HTTPS, 플러그인 stdio |
| Hindsight (1.2.2, 11-19) | Postgres 행, 수정·삭제·무효화 API (`engine/memory_engine.py`) | 선택적 감사 로그(보존 기간 후 삭제), 해시 없음 (`engine/audit.py`) | 발생 시점 + 언급 시점, 무효화 | 정규식 비밀값 제거만. 주입 탐지는 클라우드 전용 | **Lindera 한국어 토크나이저(선택)**, multilingual-e5-small | HTTP `/mcp/` |
| Cognee (1.6.10, 11-18) | 고칠 수 있는 그래프·벡터 + 별도 추가 전용 출처 원장 | **SHA-256 체인 원장 + `verify_chain` + HMAC 외부 고정.** 기본 꺼짐(`PROVENANCE_TRACKING=False`), 그래프 내용은 체인 밖, 비대칭 서명 없음, `storage.clear()`로 삭제 가능 (`cognee/modules/provenance/`) | 원장에 valid_from/until | 확인 못 함 | 한국어 분석기 없음 | stdio·SSE·HTTP |
| Graphiti (0.31.2, 10-20 / 11-19) | 고칠 수 있는 그래프 | 간선별 출처 에피소드. 해시 없음 | **이중 시간(valid/invalid + created/expired)**, 충돌은 LLM이 판단해 무효화 | README가 "주입 방어 없음" 명시 | 없음 | HTTP·stdio |
| Letta (letta-code 0.34.66, 11-19) | Markdown git 저장소 | git 이력만, 커밋 서명 강제 해제 (`src/agent/memory-git-signing.ts`) | 없음 | 없음 | — | MCP 클라이언트이지 기억 서버 아님 |
| basic-memory (1.0.0, 10-29 / 11-19, AGPL) | 고칠 수 있는 Markdown + SQLite 색인 | `checksum`은 재임베딩 판단용 | 작성자가 쓰는 유효기간 | 훅에서 그래프 텍스트를 구획으로 감쌈 | **한글 n-gram 색인** | stdio·HTTP·SSE |
| deja-vu (0.24.3, 11-19) | 대화 기록 색인 | 비밀값 제거만 | 없음 | 없음 | **CJK bigram (한글 포함)** | stdio |
| 공식 MCP `memory` (servers 2.5.0, 11-18) | JSONL 통째로 다시 씀 | 없음 | 없음 | 없음 | 부분 문자열 | stdio·HTTP |

**서명·해시 체인 기억을 내세우는 프로젝트 (2025–2026):**

| 프로젝트 | 무엇을 하나 | 약점 (확인) |
| :--- | :--- | :--- |
| sattyamjjain/mnemo (Rust, MCP) | SHA-256 체인 3개, 항상 켜짐 | 자체 문서(`docs/security/known-limitations.md`): 키가 없어 쓰기 권한자가 다시 쓰기·꼬리 삭제·되돌리기 가능, `recall`이 검증 안 함 |
| SaravananJaichandar/world-model-mcp | 해시 체인 + Merkle + Ed25519·SLH-DSA 기간 서명 + Rekor 고정 (선택) | 키를 서버가 만들어 DB 옆에 둠(`audit_keys.py`). 사람 승인 기억 서명이 아니라 감사 기간 서명 |
| Perseus-Computing-LLC/kibisis | 기억마다 HMAC, 저널 머리 HMAC로 꼬리 삭제 탐지, 시점 질의 | 대칭키라 검증자가 위조도 가능, 저장소 밖 되돌리기 기준 없음 (`SECURITY.md`) |
| 28naem-del/mnemosyne | 통합 diff·게이트 영수증만 Ed25519 서명 | 기억마다 서명 아님, 키 파일이 DB 옆 |
| 기타 (README 주장만, 추정) | tradememory-protocol, engrava, zaxy, dent8, orreth, atmem, OWASP agent-memory-guard | 내부 미확인 |

**결론 (추정):** 해시 체인은 흔하다. "서버 쓰기 경로와 분리된 사람 보유 키로 기억 내용에 서명 + 검색 시 검증 + 저장소 밖 서명 기준점 + 이중 시간 + 한국어"를 함께 갖춘 배포 제품은 찾지 못했다.

## 2. 기억 오염 연구와 MCP 규격

### 2.1 공격

| 논문 | 위협 모델 | 보고값 |
| :--- | :--- | :--- |
| AgentPoison, NeurIPS 2024 ([2407.12784](https://arxiv.org/abs/2407.12784)) | 기억·RAG에 트리거 최적화 항목 삽입 | 검색 82%, 종단 63%, 오염 비율 0.1% 미만 |
| MINJA ([2503.03704](https://arxiv.org/abs/2503.03704)) | 질의 권한만 있는 일반 사용자가 에이전트가 스스로 쓰게 유도 | 주입 98.2%, 공격 76.8% |
| Zombie Agents ([2602.15654](https://arxiv.org/abs/2602.15654)) | 공격자 웹 콘텐츠가 정상 기억 갱신 경로로 유입 | 세션 단위 필터로 부족하다고 결론 |
| Sleeper Memory Poisoning ([2605.15338](https://arxiv.org/abs/2605.15338)) | 심어둔 문서·웹·저장소, 지연 트리거로 "사용자에 대한 가짜 사실" 기록 | 기록률 최대 99.8%, 성공 주입 중 60–89%가 의도 행동으로 |
| Bad Memory, UW ([2607.14611](https://arxiv.org/abs/2607.14611)) | Claude Code·Codex 기억 파일 | 기억 파일 사전 주입은 현재·이후 세션에 지속 |
| MemSecBench ([2607.27080](https://arxiv.org/abs/2607.27080)) | 장기 기억 내 악성 지시 310건 | 지속 84.2%, 종단 50.3% |
| MCPTox ([2508.14925](https://arxiv.org/abs/2508.14925)) | 악성 MCP 도구 설명문 | 최고 72.8%, 평균 36.5% |

### 2.2 방어

* **MemLineage** ([2605.14421](https://arxiv.org/abs/2605.14421), 2026-05-14): 사용자별 Ed25519 + RFC 6962 Merkle 로그 + 가중 파생 그래프 + 민감 행동 차단. 자체 시험 환경에서 공격 성공 0. **AgentDojo 연결 실험에서 서명만 있는 기준선은 6개 쌍 모두 실패.** 확인 (초록 직접 대조). 배포 코드는 찾지 못함 (GitHub 검색의 동명 저장소는 무관).
* **CaMeL** ([2503.18813](https://arxiv.org/abs/2503.18813)): 값에 권한·출처 꼬리표, 도구 호출 시점 정책 검사. 신뢰 꼬리표를 행동 시점에 강제한 선례.
* **A-MemGuard** ([2510.02373](https://arxiv.org/abs/2510.02373), ICML 2026): 관련 기억 간 합의 검사 + 교훈 기억. 출처 기반 아님.
* **TMA-NM** ([2606.24322](https://arxiv.org/abs/2606.24322), 단독 저자) / **Nous** ([2606.22030](https://arxiv.org/abs/2606.22030)): 내용·계보 기반 신뢰는 요약·도구 반향으로 세탁될 수 있음, 출처를 쓰기 시점에 묶어야 함.

### 2.3 서명·출처가 막는 것과 못 막는 것 (추정)

* 막는 것: 서버 밖에서의 저장소 수정·삽입·순서 변경, 저장소 밖 기준점이 있을 때의 삭제·되돌리기, 에이전트 쓰기 경로로 들어온 기억의 신뢰 오표시.
* 못 막는 것: 내용의 참·거짓, 승인 피로로 사람이 서명한 악성 사실, 서명 전에 오염된 원문, 다른 경로를 거친 세탁, 꼬리표를 무시하는 모델(행동 차단 필요), 검색 단계 트리거 공격, 같은 기기 키 탈취, 다른 MCP 서버의 도구 오염.

### 2.4 MCP 규격

* 최신 규격 **2026-07-28** (이전 2025-11-25). 확인 ([changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)).
  * 무상태 전환: `initialize`·`Mcp-Session-Id` 제거, 버전·기능은 요청 `_meta`로
  * `server/discover` 추가
  * Elicitation은 다회 왕복 요청으로
  * Roots·Sampling·Logging 폐지 예정
  * `structuredContent` 임의 JSON
  * JSON Schema 2020-12
* stdio 서버는 OAuth를 쓰지 않고 환경에서 자격을 받는다. 로컬 HTTP는 토큰이나 유닉스 소켓으로 제한할 것. 확인 ([보안 모범 사례](https://modelcontextprotocol.io/specification/2026-07-28/basic/security_best_practices)). 기억 오염 전용 절은 없다.
* SDK (PyPI 확인):
  * 공식 `mcp` 2.3.0 (2026-10-02): v2가 2026-07-28 구현, 2025-11-25 클라이언트 지원, `FastMCP`가 `MCPServer`로 이름 변경 ([what's new](https://py.sdk.modelcontextprotocol.io/whats-new/))
  * `fastmcp` 4.2.2 (2026-11-18)

## 3. 변조 탐지 표준

| 표준 | 구현 (날짜) | 채택 |
| :--- | :--- | :--- |
| RFC 6962 / [RFC 9162](https://www.rfc-editor.org/rfc/rfc9162) Merkle 해시 | 직접 구현 (규격 시험 벡터로 확인). pymerkle 7.0.0 (2026-10-18) 참고 | 채택 |
| [C2SP tlog-checkpoint](https://c2sp.org/tlog-checkpoint) + [signed-note](https://c2sp.org/signed-note) | 성숙한 Python 구현 없음 (tlog-scales 0.0.3 작업 중) → `cryptography`로 직접 | 채택 |
| DSSE (PAE) | securesystemslib 1.6.0 (2026-10-20) | 직렬화 방식만 채택 |
| Sigstore Rekor | sigstore-python 4.5.1 (2026-10-20) | 선택적 외부 증인 후보, 후순위 |
| W3C PROV | 용어만 차용 | 필드 이름 |
| RFC 8785 JCS | `rfc8785` 0.1.4 (2024-09-27, 2026 활동 없음) | 미채택 — 저장 바이트를 정본으로 |
| Tessera·Trillian, C2PA | Go 서비스 / 미디어용 | 과함, 미채택 |

## 4. 로컬 실측

**SQLite FTS5 trigram과 한국어** (Python 3.14.4, SQLite 3.53.0, 2026-11-20):

| 질의 | 결과 |
| :--- | :--- |
| `MATCH '서울에'` (3글자) | 찾음 |
| `MATCH '서울'` (2글자) | **못 찾음** (trigram은 3글자 이상만 색인 조회) |
| `LIKE '%서울%'` | 찾음 (색인 가속 없음) |

→ 한국어 2글자 단어가 흔하므로 trigram 단독은 기본 검색이 될 수 없다 (판단). 형태소 분석(`kiwipiepy`)·2-gram을 비교 측정한다.

## 5. 이중 시간 모델

Zep/Graphiti ([2501.13956](https://arxiv.org/abs/2501.13956)): 간선마다 유효 시간(`t_valid`/`t_invalid`)과 기록 시간(`t'_created`/`t'_expired`). 새 사실이 옛 사실과 충돌하면 옛 간선의 `t_invalid`를 닫고 삭제하지 않는다. 확인. 추가 전용 로그는 기록 시간을 자동으로 주므로, 유효 시간만 서명 대상 내용에 넣고 무효화는 새 기록으로 한다 (판단).

## 6. 구현 전 확인 (2026-11-20, 이 맥: M5 Max, macOS 26.6.2, Python 3.14.4)

| 항목 | 결과 | 근거 |
| :--- | :--- | :--- |
| C2SP signed-note 서명 유형 | `0x01` Ed25519, `0x02` ECDSA, `0x04` 타임스탬프 Ed25519 공동 서명, `0x05` RFC 6962 STH, `0x06` ML-DSA-44, **`0xff` 미배정 유형용 예약(뒤에 충돌 가능성이 낮은 식별자)**. 키 ID = `SHA-256(키 이름 ‖ 0x0A ‖ 유형 ‖ 공개키)[:4]` | 확인: [C2SP signed-note.md](https://github.com/C2SP/C2SP/blob/main/signed-note.md) Signature types |
| Argon2id | `cryptography` 50.0.2에 `Argon2id` KDF 있음. RFC 9106 §4 두 번째 권장값(64 MiB, t=3, p=4, 솔트 16바이트) 1회 유도 32 ms | 확인: 로컬 실측 |
| 빌드·시험 도구 | `uv_build` 0.13.9 (2026-11-17), `pytest` 9.2.0 (2026-10-27), `hypothesis` 6.170.15 (2026-11-06) | 확인: PyPI JSON API |
| Python 3.14 휠 | `mcp`·`typer`·`platformdirs` 순수 Python/abi3, `cryptography`·`kiwipiepy` cp314 휠 있음. 지원 하한은 `typer`·`platformdirs`의 `>=3.11` | 확인: PyPI JSON API |
| 시작 훅 검사 | `uv sync` 후 `.pth`는 편집 설치용 `gonlith.pth`(프로젝트 `src` 절대 경로) 1개. 임의 `import os` `.pth`와 프로젝트 밖 경로 `.pth`를 넣은 복제 환경에서 둘 다 검출(종료 코드 1), 원래 환경은 통과(0) | 확인: 로컬 실측 |
| 비밀값 검사 | gitleaks 작업 트리 검사 결과 유출 0건 | 확인: 로컬 실측 |
| Merkle 구현 근거 | pymerkle 7.0.0은 GPLv3+ → Apache-2.0 패키지 의존성으로 쓰지 않음. 시험 벡터는 transparency-dev/merkle `testonly/constants.go` (Apache-2.0, 커밋 75a6539d, 2026-11-19)의 잎 입력 8개·루트 9개 | 확인: PyPI 분류자, 저장소 복제 |
| C2SP tlog-checkpoint | 본문 3줄(원점·크기·base64 루트), 이후 확장 줄은 선택이며 "권장하지 않음"(감사 불가, 일부 서명 방식이 서명 안 함). Ed25519 note 서명은 본문 전체를 서명 | 확인: [C2SP tlog-checkpoint.md](https://github.com/C2SP/C2SP/blob/main/tlog-checkpoint.md) |

## 7. 관리·수집 기능 경쟁 조사 (2026-11-21)

각 README·문서·코드에서 확인했다. 확인하지 못한 칸은 "미확인"이다.

| 프로젝트 (라이선스, 최근) | 설치·로컬 모델 | 관리 화면 | 수집 | 자동 정리 | 여러 클라이언트 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| mem0 OSS (Apache-2.0, 2.2.1, 2026-09-25) | 라이브러리는 pip. 대시보드는 Docker+Postgres+`OPENAI_API_KEY`. Ollama 설정 가능 | 사용자별 탐색·삭제, LLM 설정. 편집·병합·되돌리기 미기재 | 텍스트·대화, 이미지(비전 모델) | 2026 알고리즘은 "ADD-only", 모순이 남음 | **공식 MCP는 호스팅 전용.** OpenMemory는 2026-07-29(#6530) 제거 |
| basic-memory (AGPL-3.0, 1.0.0, 2026-10-29) | `uv tool install`, 클라이언트 JSON 직접 편집, 로컬 FastEmbed | 로컬 GUI 없음(Obsidian·편집기). 유료 클라우드에 웹 앱·스냅샷 | Markdown만, 폴더 양방향 동기 | 자동 정리 없음 | 같은 폴더 공유로 가능 |
| Hindsight (MIT, 1.2.3, 2026-11-19) | Docker+LLM 키 또는 pip. Ollama·LM Studio, 로컬 모델 | **가장 풍부**: 편집·무효화·문서·관찰 이력·엔티티·감사·zip 내보내기 | PDF·DOCX·PPTX·XLSX·이미지·txt/md(markitdown), Obsidian 단방향 `--watch`. URL 수집 미발견 | LLM 배경 통합, 거의 중복·모순 자동 조정(이력 유지), 사람 확인 미발견 | 서버 1개, 은행별 MCP 엔드포인트 |
| Cognee (Apache-2.0, 1.6.10, 2026-11-18) | uv, 키 없이 로컬 GLiNER. UI는 Node, MCP는 Docker·소스 | 데이터셋·그래프·검색·활동 화면. 편집·병합·되돌리기 미기재 | 텍스트·CSV·PDF·이미지·오디오·비디오·코드, 웹 스크레이퍼, Drive·Gmail | 선택형 LLM 모순 검사(간선만 추가, 해결 안 함) | HTTP/SSE |
| Letta (Apache-2.0, letta-code 0.34.68) | npm/uv·데스크톱 앱, 클라우드 기본 | 메모리 블록, git 이력 | 문서 저장소 아님 | 에이전트가 스스로 재작성 | 공유 MCP 서버 아님 |
| Khoj (AGPL-3.0, 안정판 1.42.10 2025-07) | pip·Docker, Ollama | 채팅·파일 관리 웹 앱 | PDF·MD·org·DOCX·이미지·Notion, 폴더 동기 | 미기재 | MCP 클라이언트일 뿐 서버 아님 |
| mcp-memory-service (Apache-2.0, 13.0.0, 2026-11-20) | pip, JSON 직접 편집, 로컬 ONNX | 탐색·편집·삭제·일괄 삭제·완전 중복 정리·JSON 내보내기. 병합·충돌·되돌리기 미기재 | PDF·DOCX·PPTX·TXT·MD 업로드, 감시 없음 | 주기적 통합, 규칙으로 옛 기억 대체 | HTTP 모드 |
| LongMemory (옛 CaviraOSS OpenMemory, Apache-2.0, npm 1.3.3 2026-08-31) | npm·Docker, Ollama | Next.js 대시보드: 탐색·수집·검색·타임라인·감쇠 | 로컬 파일·Markdown·웹·피드·클라우드 문서(목록 기준) | 검색 시점 대체·모순 검사 | stdio·HTTP |

* 확인 못 한 것: LongMemory 저장소 릴리스 날짜(GitHub API 제한으로 npm 날짜 사용), Cognee·Khoj 화면의 편집·병합 기능(페이지 이름·문서만 봄).
* 결론(판단): 사람 확인 정리, 사용자용 되돌리기, 일반인 설치, 파일+URL+감시 폴더 조합이 비어 있다. `docs/design.md` §3.

## 8. 수집 라이브러리 확인 (PyPI JSON API, 2026-11-21)

| 패키지 | 버전 (날짜) | 라이선스 | 판정 |
| :--- | :--- | :--- | :--- |
| markitdown | 0.1.9 (2026-10-21) | MIT | 후보 (Office·PDF→Markdown) |
| docling | 2.151.1 (2026-11-19) | MIT | 선택 기능 후보 (무거움, OCR·표) |
| pypdf | 7.1.1 (2026-11-18) | BSD-3-Clause | 후보 (PDF 텍스트) |
| trafilatura | 2.3.1 (2026-10-06) | Apache-2.0 | 후보 (웹 본문) |
| watchfiles | 1.3.0 (2026-09-21) | MIT | 후보 (폴더 감시) |
| watchdog | 7.1.0 (2026-11-05) | Apache-2.0 | 대안 |
| chonkie / semchunk | 1.7.0 (2026-07-07) / 4.1.1 (2026-06-13) | MIT | 조각 나누기 대안 (제목 기준 직접 분할과 S5에서 비교) |
| pymupdf | 2.1 (2026-11-02) | **AGPL** | 제외 |
| html2text | 2025.4.15 | **GPL-3.0+**, 2026 릴리스 없음 | 제외 |
| unstructured | 0.27.37 (2026-11-06) | Apache-2.0 | 제외 (`requires_python <3.14`) |
| httpx | 0.28.1 (2024-12-06) | BSD | 2026 릴리스 없음 → 직접 의존 금지, `mcp`의 간접 의존성으로만 |

## 9. 평가용 공개 데이터셋 (2026-11-21, HF API로 날짜·크기 확인)

평가에만 쓰고 재배포하지 않는다. 받는 목록과 고정 커밋은 `eval/datasets.toml`, 파일 SHA-256은 `eval/datasets.lock.json`, 캐시는 `eval/.cache/`(git 제외)에 둔다. 2026년에 공개되었거나 2026년에 갱신된 데이터만 쓴다(AGENTS.md).

**받은 것 (텍스트 6종, 27 MB):**

| 용도 | 데이터셋 | HF 최초 게시 / 갱신 | 원본 | 라이선스 | 받은 파일 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 장기 대화 기억 QA (한국어) | [NAMJOON/longmemeval-oracle-ko](https://huggingface.co/datasets/NAMJOON/longmemeval-oracle-ko) | 2026-09-27 / 2026-09-27 | LongMemEval 2024-10 (arXiv 2410.10813) 기계 번역 | MIT | `korean_only.jsonl` 16.1 MB. oracle 분할이라 방해 세션 없음 |
| 한국어 위키 검색 | [nlpai-lab/miracl-multilingual-triplets](https://huggingface.co/datasets/nlpai-lab/miracl-multilingual-triplets) | 2026-07-16 / 2026-07-16 | MIRACL | Apache-2.0 | `miracl_ko_triplet.parquet` 1.8 MB |
| 한국어 문단 검색 | [mteb/belebele](https://huggingface.co/datasets/mteb/belebele) | 2026-02-26 / 2026-02-26 | Belebele (FLORES 문단) | CC-BY-SA-4.0 | `kor_Hang.jsonl` 1.5 MB (문단 488·질문 900) |
| 한국어 다단계 문서 검색 | [whooray/Ko-StrategyQA](https://huggingface.co/datasets/whooray/Ko-StrategyQA) | 2026-02-21 / 2026-02-21 | StrategyQA 2021 | 카드에 없음 → 내부 평가만 | 7.6 MB (문서 9,251·dev 질의 592) |
| 기억 모순·갱신 판별 | [eskora/memory-contradiction-pairs-hard](https://huggingface.co/datasets/eskora/memory-contradiction-pairs-hard) | 2026-11-11 / 2026-11-11 | 개인 제작, 검증 이력 없음 | CC-BY-4.0 | test·valid 0.16 MB. S8 전에 표본 품질 확인 |
| 한국어 의역 판별 | [mteb/PawsXPairClassification](https://huggingface.co/datasets/mteb/PawsXPairClassification) | 2025-06-19 / 2026-02-24 | PAWS-X 2019-08 (arXiv 1908.11828) | Google 약관상 자유 사용 (카드: other) | ko test·validation 0.7 MB |

**음성 (S5b 때 받음, 사용자 확인 후):**

| 데이터셋 | HF 최초 게시 / 갱신 | 원본 | 라이선스 | 한국어 크기 |
| :--- | :--- | :--- | :--- | :--- |
| [google/fleurs](https://huggingface.co/datasets/google/fleurs) ko_kr (낭독) | 2022-04-19 / 2026-05-15 | 2022-05 (arXiv 2205.12446) | CC-BY-4.0 | 1.76 GB |
| [MagicHub/korean-conversational-speech-corpus](https://huggingface.co/datasets/MagicHub/korean-conversational-speech-corpus) (대화) | 2026-06-09 / 2026-06-15 | 원본 공개일 카드에 없음 | 학술 연구 전용 | 619 MB |
| [google/svq](https://huggingface.co/datasets/google/svq) ko_kr (짧은 음성 질문, 검색 연결) | 2025-05-12 / 2026-09-24 | — | CC-BY-4.0 | 깨끗한 음성만 167 MB, 잡음 포함 전체 865 MB |

**2026 기준으로 제외 (확인):**

| 데이터 | 마지막 갱신 | 대신 쓰는 것 |
| :--- | :--- | :--- |
| mteb/AutoRAGRetrieval | 2025-05 | Belebele·MIRACL·Ko-StrategyQA |
| allganize/RAG-Evaluation-Dataset-KO (PDF) | 2024-11 | 2026 한국어 PDF 질의 데이터를 찾지 못함. S5에서 공개 한국어 PDF(공공누리 1유형 등)로 직접 만든다 |
| PAWS-X 원본 저장소 | 2024-01 | mteb 2026 사본 |
| LoCoMo | 2024-08 (CC BY-NC) | LongMemEval-ko |
| MemoryBank | 2023-05 | LongMemEval-ko |
| Zeroth-Korean | 2022/2024 | FLEURS·MagicHub |
| KsponSpeech (AI Hub) | 2019-05 | 사용자가 직접 받으면 로컬 평가만 |
| xiaowu0162/longmemeval-cleaned (영어 원본) | HF 2025-09 (GitHub 2026-05) | 필요 시 영어 oracle 15 MB만. M 분할은 2.7 GB |

**조사 과정에서 바로잡은 것:**
* 처음 조사에서는 "평가 도구 mteb가 2026-11에 갱신됐으니 2026 규칙을 충족한다"고 판단했다. 이는 데이터 자체가 아닌 도구 기준이라 잘못이다. 데이터 갱신일로 다시 걸렀다.
* 처음 크기 보고에서 FLEURS ko를 "수백 MB"로 적었다. 실제는 1.76 GB다.

## 10. 음성 처리 구성 요소 (2026-11-21)

| 구분 | 후보 | 라이선스 | 날짜 | 한국어 | 비고 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 음성 인식 (기본 후보) | whisper-large-v3-turbo + [whisper.cpp](https://github.com/ggml-org/whisper.cpp) v1.9.5 | MIT | 가중치 2024-10, 실행기 2026-10-06 | 지원 (카드에 한국어 수치 없음) | Metal·CUDA·CPU, 809M |
| 음성 인식 (비교 후보) | [Qwen3-ASR-1.7B/0.6B](https://huggingface.co/Qwen/Qwen3-ASR-1.7B) | Apache-2.0 | 2026-01-28 | 지원 (한국어 수치 없음) | MLX·GGUF 이식본 |
| 음성 인식 (무거운 선택) | [VibeVoice-ASR](https://huggingface.co/microsoft/VibeVoice-ASR) | MIT | 2026-01 | 태그만 | 8.7B, 화자 구분 내장, 48 GB에 들어감 (추정) |
| 참고 수치 | nemotron-3.5-asr-streaming-0.6b | OpenMDW-1.1 | 2026-05 | FLEURS ko CER 7.12 (저자 보고) | CUDA 중심 |
| 화자 구분 | [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) | Apache-2.0 | 2026-11 | — | 토큰 불필요, 3개 OS |
| 화자 구분 (대안) | pyannote.audio 4.1.1 + community-1 | MIT 코드 / CC-BY-4.0 가중치 | 2026-11-19 | — | HF 토큰·약관 동의 필요(게이트) |
| 음성 구간 검출 | [silero-vad](https://github.com/snakers4/silero-vad) 6.2.3 | MIT | 2026-09 | — | TEN VAD는 경쟁 금지 조건이 붙어 제외 |

* 제외 (확인):
  * Parakeet-v3·Canary-1b-v2: 한국어 없음
  * Kotoba: 일본어 전용
  * SenseVoiceSmall: 자체 라이선스
  * mlx-whisper: 2025-08 이후 정체
* **MCP와 음성 (확인, [schema 2026-07-28](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/schema/2026-07-28/schema.ts)):**
  * `AudioContent`는 도구 결과·프롬프트 메시지 같은 **출력**에만 있다. 도구 **입력**은 JSON 인자라 음성은 base64 문자열이나 파일 경로로만 넘길 수 있다.
  * 대화 음성이나 전체 대화록을 MCP 서버에 넘기는 클라이언트는 찾지 못했다 (추정).
  * 음성 모드에서 MCP 도구 호출은 Claude(2026-07)와 ChatGPT(2026-09)에 생겼다(2차 출처). 다만 사용자 제보로는 사용자 정의 MCP 도구가 실패한 사례가 있다.
* **판단:** 음성은 이 순서로 들어온다:
  1. 녹음 파일 가져오기
  2. 대본·대화 내보내기 파일 가져오기
  3. 음성 모드 AI가 대화 중 텍스트로 `remember` 호출

  실시간 음성 연결은 지금 규격으로는 없다.
