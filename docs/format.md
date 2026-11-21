# Gonlith 데이터 형식 규격

> 설계 정본: [`docs/design.md`](design.md) §6·§7. 이 문서는 다른 구현이 Gonlith 로그를 바이트 단위로 같게 읽고 검증할 수 있게 하는 규격이다.
> **상태:** 1차 (S1 범위, 설계 4판 반영). `genesis`·`memory` 항목, 엄격 판독, 체크포인트를 정의한다. `note`·`document`·`revise`·`archive`·`delete`·합치기 항목은 각 단계에서 추가한다. **공개 전까지 형식 판 1은 확정되지 않으며, 그 전에 만든 로그는 버린다** (`docs/design.md` §6.7).
> 규범 용어 MUST/SHOULD는 RFC 2119·8174 뜻으로 쓴다.

## 1. 로그

* 로그는 항목의 순서열이다. 각 항목은 0부터 연속하는 **위치**를 가진다. 기억 `id`는 그 항목의 위치다.
* 위치 0은 `genesis` 항목이어야 하고(MUST), 그 밖의 위치에 `genesis`가 있으면 안 된다(MUST NOT).
* 항목 바이트는 한 번 쓰면 바뀌지 않는다. 형식이 바뀌어도 기존 항목을 다시 쓰지 않는다.

## 2. 항목 바이트

### 2.1 봉투

항목 바이트 = DSSE PAE ([DSSE 규격](https://github.com/secure-systems-lab/dsse/blob/master/protocol.md)):

```
"DSSEv1" SP LEN(type) SP type SP LEN(body) SP body
```

* `SP`는 `0x20`이다.
* `LEN`은 바이트 길이를 앞자리 0 없는 ASCII 10진수로 쓴 값이다.
* `type`은 형식 판을 담는다. 판 1: `application/vnd.gonlith.entry.v1+json`
* 저장소는 이 바이트 전체를 그대로 보관한다.
* 검증기는 봉투를 분해한 뒤 `type`이 아는 판인지 확인한다. 모르는 판이면 거부한다.

### 2.2 Merkle 잎

* 잎 해시 = `SHA-256(0x00 ‖ 항목 바이트)`
* 트리 루트는 RFC 6962 §2.1의 MTH 정의를 따른다. 빈 트리의 루트는 `SHA-256("")`이다.

### 2.3 본문 정규 인코딩

본문은 UTF-8로 인코딩한 JSON 객체 하나다. 같은 뜻에 바이트 표현이 하나만 있도록 아래 정규 인코딩을 MUST로 지킨다.

| 요소 | 규칙 |
| :--- | :--- |
| 공백 | 토큰 사이 공백 없음. 구분자는 `,`와 `:` |
| 객체 키 | 유니코드 코드 포인트 오름차순. 중복 키 금지 |
| 문자열 | `"`와 `\`, U+0000–U+001F만 이스케이프한다. `\b` `\f` `\n` `\r` `\t`는 짧은 형식, 나머지 제어 문자는 `\u00xx`(소문자 16진수). 그 밖의 문자(비ASCII 포함)는 UTF-8 그대로. 짝 없는 대리 코드 포인트 금지 |
| 숫자 | 정수만. 부호는 음수일 때 `-`만, 앞자리 0 없음. 실수·지수·`NaN`·`Infinity` 금지 |
| 리터럴 | `true`, `false`, `null` |

**엄격 판독:** 검증기는 아래 순서로 본문을 읽는다.
1. UTF-8로 디코딩한다.
2. JSON으로 파싱한다. 중복 키, 실수, `NaN`·`Infinity`가 나오면 거부한다.
3. 위 규칙으로 다시 인코딩해 원래 본문 바이트와 같은지 비교한다. 다르면 거부한다.
4. §3의 종류별 필드 집합과 정확히 일치하는지 확인한다. 빠진 필드나 모르는 필드가 있으면 거부한다.

### 2.4 공통 값 형식

| 이름 | 형식 |
| :--- | :--- |
| 시각 (`timestamp`) | RFC 3339 UTC, 소수점 아래 6자리 고정, `Z` 접미: `YYYY-MM-DDTHH:MM:SS.ffffffZ` |
| 날짜 또는 시각 (`instant`) | `YYYY-MM-DD` 또는 `timestamp` |
| 해시 (`hex32`) | SHA-256 결과 32바이트의 소문자 16진수 64자 |
| 바이트 (`b64`) | RFC 4648 §4 표준 base64, `=` 채움, 정규형(§3.5)만 |

## 3. 항목 종류

모든 본문에는 `kind` 필드가 있다. 아래 표에 없는 `kind`는 거부한다.

### 3.1 `genesis`

| 필드 | 형식 | 뜻 |
| :--- | :--- | :--- |
| `kind` | `"genesis"` | |
| `origin` | 문자열 | 로그 원점 이름: `gonlith.invalid/` + 무작위 16바이트의 소문자 16진수 32자. `.invalid`는 RFC 2606 예약 최상위 도메인이라 실제 도메인과 겹치지 않는다 |
| `created_at` | `timestamp` | 참고값 |

* 기본 모드의 genesis에는 키가 없다 (`docs/design.md` §13.3). 보호 모드의 키는 그 단계에서 별도 항목 종류로 정의한다 (`docs/protection-mode.md`).
* 첫 실행 때 서버가 자동으로 genesis를 만든다.

### 3.2 `memory`

| 필드 | 형식 | 뜻 |
| :--- | :--- | :--- |
| `kind` | `"memory"` | |
| `space` | 비어 있지 않은 문자열 | 기억 공간 (접근 제어 아님) |
| `category` | 비어 있지 않은 문자열 | 기억 분류. 허용 값은 설정 파일이 정하고, 검증기는 형식만 확인 |
| `content_hash` | `hex32` | `SHA-256(salt ‖ 내용 UTF-8 바이트)` (§4) |
| `valid_from` | `instant` 또는 `null` | 주장값 |
| `valid_to` | `instant` 또는 `null` | 주장값. 둘 다 있으면 같은 형식(`YYYY-MM-DD`끼리 또는 `timestamp`끼리)이어야 하고 `valid_from` < `valid_to` |
| `recorded_at` | `timestamp` | 참고값. 순서의 정본은 위치 |
| `writer` | `"agent"` 또는 `"human"` | 쓴 쪽이 밝힌 값 |
| `client` | 문자열 또는 `null` | 클라이언트가 밝힌 이름. 검증되지 않음 |
| `session` | 비어 있지 않은 문자열 | 서버가 발급한 세션 식별자 |
| `source` | `"conversation"`·`"tool_output"`·`"web"`·`"file"`·`"user_typed"`·`"unknown"` 중 하나 | 쓰는 쪽이 밝힌 값 |
| `derived_from` | 정수 배열 | 이 항목보다 앞선 `memory` 위치들. 오름차순, 중복 없음 |

## 4. 내용

* 내용은 로그 밖 `contents` 저장소에 위치별로 `salt`와 함께 둔다.
* `salt`는 16바이트 무작위 값이다(NIST SP 800-132 §5.1의 최소 128비트).
* 내용은 비어 있지 않은 UTF-8 바이트이며, 받은 그대로 저장한다(정규화하지 않음).
* 검증기는 `SHA-256(salt ‖ 내용)`이 항목의 `content_hash`와 같은지 확인한다. 내용이 없으면 `delete` 항목(S11에서 정의)이 있을 때만 허용하고, 없으면 그 기억은 `broken`이다.

## 5. 체크포인트

C2SP [tlog-checkpoint](https://c2sp.org/tlog-checkpoint) 노트 본문:

```
<origin>
<트리 크기, 앞자리 0 없는 10진수>
<루트 해시 b64>
```

* 각 줄은 `0x0A`로 끝난다.
* 서명되지 않은 체크포인트는 `gonlith verify`가 출력하는 현재 상태 요약이다.
* 기본 모드에서 체크포인트는 무결성 경고용 기준점이다(데이터 폴더에 저장, `docs/design.md` §13.2).
* 보호 모드의 서명 승인문은 이 세 줄 뒤에 확장 줄로 동작 목록을 붙인 signed-note로 정의할 예정이다(`docs/protection-mode.md` §6.5).

## 6. SQLite 저장 (참고 구현)

규격의 일부가 아니라 참고 구현의 배치다. 다른 구현은 위 §1–§5만 지키면 된다.

| 테이블 | 열 | 비고 |
| :--- | :--- | :--- |
| `log` | `position INTEGER PRIMARY KEY`, `entry BLOB NOT NULL` | `UPDATE`·`DELETE` 거부 트리거 (실수 방지용, 보안 장치 아님) |
| `contents` | `position INTEGER PRIMARY KEY`, `salt BLOB NOT NULL`, `content BLOB NOT NULL` | 진짜 삭제(S12) 때 행을 지움 |
