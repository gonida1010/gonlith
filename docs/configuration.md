# Gonlith 설정값과 출처

> 설계 정본: [`docs/design.md`](design.md) §8.8 — 출처 없는 상수는 두지 않는다. 기본값은 `src/gonlith/defaults.toml`, 사용자 덮어쓰기는 데이터 폴더의 `config.toml`이다.
> 보호 모드(선택)의 키·권한은 설정 파일이 아니라 서명된 로그에 둔다 (`docs/protection-mode.md` §6.8).

| 키 | 기본값 | 출처·근거 | 재검토 |
| :--- | :--- | :--- | :--- |
| `storage.database_file` | `gonlith.db` | 이름일 뿐 동작에 영향 없음 | — |
| `storage.busy_timeout_seconds` | `5.0` | Python `sqlite3.connect`의 문서화된 기본 `timeout` 값 ([docs.python.org](https://docs.python.org/3/library/sqlite3.html#sqlite3.connect)) | 확인: 16개 프로세스 동시 쓰기 최대 대기 302.9 ms로 여유 충분 (`docs/measurements/s1-record-layer.md` §4) |

**코드 상수 (형식 규격이 정한 값, 설정으로 바꾸면 안 됨):** 항목 타입 문자열, 원점 접두 `gonlith.invalid/`, 솔트 16바이트, 원점 무작위 16바이트 — 근거는 `docs/format.md` §2–§4.
