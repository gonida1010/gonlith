# Gonlith 설정값과 출처

> 설계 정본: [`docs/design.md`](design.md) §8.8 — 출처 없는 상수는 두지 않는다. 기본값은 `src/gonlith/defaults.toml`, 사용자 덮어쓰기는 데이터 폴더의 `config.toml`이다.
> 보호 모드(선택)의 키·권한은 설정 파일이 아니라 서명된 로그에 둔다 (`docs/protection-mode.md` §6.8).

| 키 | 기본값 | 출처·근거 | 재검토 |
| :--- | :--- | :--- | :--- |
| `storage.database_file` | `gonlith.db` | 이름일 뿐 동작에 영향 없음 | — |
| `storage.busy_timeout_seconds` | `5.0` | Python `sqlite3.connect`의 문서화된 기본 `timeout` 값 ([docs.python.org](https://docs.python.org/3/library/sqlite3.html#sqlite3.connect)) | 확인: 16개 프로세스 동시 쓰기 최대 대기 302.9 ms로 여유 충분 (`docs/measurements/s1-record-layer.md` §4) |
| `storage.fullfsync` | `true` | 켜면 저장 p50 3.9 ms, 끄면 0.09 ms. macOS `fsync`는 드라이브 캐시를 비우지 않아 전원 차단 시 마지막 저장이 사라질 수 있음 (`docs/measurements/s2-mcp-core.md` §2) | — |
| `spaces.personal` | `personal` | 개인 공간 이름. 검색은 기본적으로 현재 공간 + 이 공간 (`docs/design.md` §11.2) | — |
| `search.tokenizer` | `bigram` | 합성 평가셋 R@5 0.942(기준선 0.575), Belebele 0.919(0.626), Ko-StrategyQA 0.616(0.367). kiwi와 차이는 −0.002~+0.018인데 설치 126 MB, 색인 생성 20배 (`docs/measurements/s2-mcp-core.md` §1, §1b) | S7 임베딩과 비교 |
| `search.default_limit` | `10` | 공개 데이터에서 2-gram R@10이 R@5보다 Belebele +0.029, Ko-StrategyQA +0.084 높음. 합성 평가셋에서는 같았음 (`docs/measurements/s2-mcp-core.md` §1, §1b). 긴 응답은 `max_output_chars`가 막음 | S7 재측정 |
| `search.max_output_chars` | `50000` | Claude Code는 텍스트 결과가 5만 자를 넘으면 대화 대신 파일로 뺀다 ([MCP 출력 제한](https://code.claude.com/docs/en/mcp-servers), 2026-11-21 확인) | 다른 클라이언트 제한 확인 시 (V4) |
| `memory.default_category`, `memory.categories` | `fact`, 7종 | `docs/design.md` §7.2 분류 목록 | — |
| `memory.default_source` | `conversation` | AI가 `source`를 생략하는 가장 흔한 경우는 대화 중 저장 | — |
| `server.*` | 안내문·도구 설명 | 코드에 넣지 않는 문구 (AGENTS.md 하드코딩 금지) | 클라이언트 시험 결과로 다듬음 |
| `text.external_open`, `text.external_close`, `text.external_notice`, `text.omitted_notice` | 구획 문구 | `docs/design.md` §14.2 | — |
| `text.nonce_bytes` | `8` | 구획 경계는 응답마다 새로 뽑는 64비트 난수다. 기억을 쓸 때는 경계를 알 수 없으므로 내용에 닫는 경계를 미리 넣어 탈출할 확률은 2⁻⁶⁴ | — |
