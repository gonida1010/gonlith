# Gonlith 로그 항목의 정규 인코딩·엄격 판독·DSSE PAE 봉투·종류별 필드 검증 (docs/format.md §2–§3)
import base64
import hashlib
import json
import re
from datetime import date, datetime, timezone

ENTRY_TYPE = "application/vnd.gonlith.entry.v1+json"
PAE_PREFIX = b"DSSEv1 "
ORIGIN_PREFIX = "gonlith.invalid/"
ORIGIN_RANDOM_BYTES = 16
SALT_BYTES = 16
ED25519_KEY_BYTES = 32
ED25519_NOTE_TYPE = b"\x01"
RECOVERY_ROLE = "recovery"
RECOVERY_RIGHTS = ["key"]
WRITERS = ("agent", "human")
SOURCES = ("conversation", "tool_output", "web", "file", "user_typed", "unknown")
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
DATE_FORMAT = "%Y-%m-%d"

TIMESTAMP_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z")
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
HEX32_PATTERN = re.compile(r"[0-9a-f]{64}")
ORIGIN_PATTERN = re.compile(re.escape(ORIGIN_PREFIX) + r"[0-9a-f]{%d}" % (ORIGIN_RANDOM_BYTES * 2))
ROLE_PATTERN = re.compile(r"[a-z0-9-]+")
DECIMAL_PATTERN = re.compile(rb"0|[1-9][0-9]*")

GENESIS_FIELDS = frozenset({"kind", "origin", "created_at", "keys"})
KEY_FIELDS = frozenset({"name", "type", "public_key", "rights"})
MEMORY_FIELDS = frozenset(
    {
        "kind",
        "space",
        "category",
        "content_hash",
        "valid_from",
        "valid_to",
        "recorded_at",
        "writer",
        "client",
        "session",
        "source",
        "derived_from",
    }
)


class EntryError(ValueError):
    pass


def encode_body(body):
    try:
        text = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        return text.encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise EntryError(f"cannot encode body: {error}") from error


def _reject_number(token):
    raise EntryError(f"non-integer number {token!r}")


def decode_body(raw):
    try:
        body = json.loads(
            raw.decode("utf-8"),
            parse_float=_reject_number,
            parse_constant=_reject_number,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise EntryError(f"invalid JSON body: {error}") from error
    if not isinstance(body, dict):
        raise EntryError("body must be a JSON object")
    if encode_body(body) != raw:
        raise EntryError("body is not in canonical encoding")
    return body


def wrap(body):
    payload = encode_body(body)
    entry_type = ENTRY_TYPE.encode("ascii")
    return b"%s%d %s %d %s" % (PAE_PREFIX, len(entry_type), entry_type, len(payload), payload)


def _take_length(data, start):
    end = data.find(b" ", start)
    if end < 0 or not DECIMAL_PATTERN.fullmatch(data[start:end]):
        raise EntryError("malformed PAE length")
    return int(data[start:end]), end + 1


def unwrap(entry):
    if not entry.startswith(PAE_PREFIX):
        raise EntryError("missing DSSEv1 prefix")
    type_length, cursor = _take_length(entry, len(PAE_PREFIX))
    entry_type = entry[cursor : cursor + type_length]
    cursor += type_length
    if len(entry_type) != type_length or entry[cursor : cursor + 1] != b" ":
        raise EntryError("malformed PAE type")
    body_length, cursor = _take_length(entry, cursor + 1)
    payload = entry[cursor:]
    if len(payload) != body_length:
        raise EntryError("PAE body length mismatch")
    if entry_type != ENTRY_TYPE.encode("ascii"):
        raise EntryError(f"unknown entry type {entry_type!r}")
    return decode_body(payload)


def now_timestamp():
    return datetime.now(timezone.utc).strftime(TIMESTAMP_FORMAT)


def _is_timestamp(value):
    if not isinstance(value, str) or not TIMESTAMP_PATTERN.fullmatch(value):
        return False
    try:
        datetime.strptime(value, TIMESTAMP_FORMAT)
    except ValueError:
        return False
    return True


def _is_date(value):
    if not isinstance(value, str) or not DATE_PATTERN.fullmatch(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _is_nonempty_text(value):
    return isinstance(value, str) and value != ""


def _is_position(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def decode_b64(value):
    if not isinstance(value, str):
        raise EntryError("base64 value must be a string")
    try:
        raw = base64.b64decode(value, validate=True)
    except ValueError as error:
        raise EntryError(f"invalid base64: {error}") from error
    if base64.b64encode(raw).decode("ascii") != value:
        raise EntryError("non-canonical base64")
    return raw


def note_key_id(name, public_key):
    return hashlib.sha256(name.encode("utf-8") + b"\n" + ED25519_NOTE_TYPE + public_key).digest()[:4]


def _require_fields(body, fields):
    if set(body) != fields:
        missing = sorted(fields - set(body))
        unknown = sorted(set(body) - fields)
        raise EntryError(f"field mismatch: missing {missing}, unknown {unknown}")


def _validate_key(key, origin):
    if not isinstance(key, dict):
        raise EntryError("key must be an object")
    _require_fields(key, KEY_FIELDS)
    name = key["name"]
    if not isinstance(name, str) or not name.startswith(origin + "/") or not ROLE_PATTERN.fullmatch(name[len(origin) + 1 :]):
        raise EntryError("key name must be <origin>/<role>")
    if key["type"] != "ed25519":
        raise EntryError("genesis keys must be ed25519")
    if len(decode_b64(key["public_key"])) != ED25519_KEY_BYTES:
        raise EntryError("ed25519 public key must be 32 bytes")
    if key["rights"] != RECOVERY_RIGHTS:
        raise EntryError(f"genesis key rights must be {RECOVERY_RIGHTS}")


def _validate_genesis(body):
    _require_fields(body, GENESIS_FIELDS)
    if not isinstance(body["origin"], str) or not ORIGIN_PATTERN.fullmatch(body["origin"]):
        raise EntryError("invalid origin")
    if not _is_timestamp(body["created_at"]):
        raise EntryError("invalid created_at")
    keys = body["keys"]
    if not isinstance(keys, list) or not keys:
        raise EntryError("genesis needs at least one key")
    for key in keys:
        _validate_key(key, body["origin"])
    if len({key["name"] for key in keys}) != len(keys):
        raise EntryError("duplicate key name")


def _validate_valid_time(valid_from, valid_to):
    for value in (valid_from, valid_to):
        if value is not None and not (_is_date(value) or _is_timestamp(value)):
            raise EntryError(f"invalid valid time {value!r}")
    if valid_from is not None and valid_to is not None:
        if _is_date(valid_from) != _is_date(valid_to):
            raise EntryError("valid_from and valid_to must use the same format")
        if not valid_from < valid_to:
            raise EntryError("valid_from must be before valid_to")


def _validate_memory(body, position):
    _require_fields(body, MEMORY_FIELDS)
    for name in ("space", "category", "session"):
        if not _is_nonempty_text(body[name]):
            raise EntryError(f"{name} must be a non-empty string")
    if not isinstance(body["content_hash"], str) or not HEX32_PATTERN.fullmatch(body["content_hash"]):
        raise EntryError("content_hash must be 64 lowercase hex characters")
    _validate_valid_time(body["valid_from"], body["valid_to"])
    if not _is_timestamp(body["recorded_at"]):
        raise EntryError("invalid recorded_at")
    if body["writer"] not in WRITERS:
        raise EntryError("invalid writer")
    if body["client"] is not None and not isinstance(body["client"], str):
        raise EntryError("client must be a string or null")
    if body["source"] not in SOURCES:
        raise EntryError("invalid source")
    derived = body["derived_from"]
    if not isinstance(derived, list) or not all(_is_position(item) for item in derived):
        raise EntryError("derived_from must be a list of positions")
    if derived != sorted(set(derived)) or (derived and derived[-1] >= position):
        raise EntryError("derived_from must be ascending, unique, and earlier than this entry")


def validate(body, position):
    kind = body.get("kind")
    if position == 0:
        if kind != "genesis":
            raise EntryError("position 0 must be genesis")
        _validate_genesis(body)
    elif kind == "memory":
        _validate_memory(body, position)
    else:
        raise EntryError(f"unknown or misplaced kind {kind!r}")


def content_hash(salt, content):
    return hashlib.sha256(salt + content).hexdigest()


def genesis_body(origin, recovery_public_key, created_at):
    return {
        "kind": "genesis",
        "origin": origin,
        "created_at": created_at,
        "keys": [
            {
                "name": f"{origin}/{RECOVERY_ROLE}",
                "type": "ed25519",
                "public_key": base64.b64encode(recovery_public_key).decode("ascii"),
                "rights": list(RECOVERY_RIGHTS),
            }
        ],
    }


def memory_body(*, space, category, digest, valid_from, valid_to, recorded_at, writer, client, session, source, derived_from):
    return {
        "kind": "memory",
        "space": space,
        "category": category,
        "content_hash": digest,
        "valid_from": valid_from,
        "valid_to": valid_to,
        "recorded_at": recorded_at,
        "writer": writer,
        "client": client,
        "session": session,
        "source": source,
        "derived_from": list(derived_from),
    }
