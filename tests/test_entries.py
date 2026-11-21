# 항목 정규 인코딩·엄격 판독·PAE 봉투·종류별 필드 검증 규칙을 정상·위반 사례로 확인하는 시험 (docs/format.md §2–§3)
import pytest

from gonlith import entries
from gonlith.entries import EntryError

ORIGIN = entries.ORIGIN_PREFIX + "0" * 32


def genesis():
    return entries.genesis_body(ORIGIN, "2026-11-20T00:00:00.000000Z")


def memory(**overrides):
    body = entries.memory_body(
        space="default",
        category="fact",
        digest="a" * 64,
        valid_from=None,
        valid_to=None,
        recorded_at="2026-11-20T00:00:00.000000Z",
        writer="agent",
        client=None,
        session="s",
        source="conversation",
        derived_from=[],
    )
    body.update(overrides)
    return body


def test_round_trip_keeps_korean_and_control_characters():
    body = memory(space="서울\n\t\x01 \x7f")
    raw = entries.encode_body(body)
    assert "서울".encode() in raw
    assert entries.decode_body(raw) == body
    assert entries.unwrap(entries.wrap(body)) == body


@pytest.mark.parametrize(
    "raw",
    [
        b'{"a":1,"a":2}',
        b'{"a":1.0}',
        b'{"a":1e3}',
        b'{"a":NaN}',
        b'{"a":-0}',
        b'{"b":1,"a":2}',
        b'{"a": 1}',
        b'{"a":"\\u00e9"}',
        b'{"a":"\\ud800"}',
        b'[1]',
        b'\xff',
    ],
)
def test_strict_decoding_rejects(raw):
    with pytest.raises(EntryError):
        entries.decode_body(raw)


TYPE = entries.ENTRY_TYPE.encode()


@pytest.mark.parametrize(
    ("entry", "reason"),
    [
        (b"DSSEv2 1 a 2 {}", "prefix"),
        (b"DSSEv1 01 a 2 {}", "length"),
        (b"DSSEv1 %d %s 2 {}" % (len(TYPE), TYPE.replace(b"v1", b"v2")), "unknown entry type"),
        (b"DSSEv1 %d %s 3 {}" % (len(TYPE), TYPE), "body length"),
        (b"DSSEv1 %d %s" % (len(TYPE), TYPE), "PAE"),
    ],
)
def test_malformed_envelopes_are_rejected(entry, reason):
    with pytest.raises(EntryError, match=reason):
        entries.unwrap(entry)


def test_valid_genesis_and_memory_pass():
    entries.validate(genesis(), 0)
    entries.validate(memory(valid_from="2026-01-01", valid_to="2026-02-01", derived_from=[1, 3]), 5)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda b: b.update(origin="example.com/log"),
        lambda b: b.update(origin=entries.ORIGIN_PREFIX + "0" * 31),
        lambda b: b.update(created_at="2026-11-20T00:00:00Z"),
        lambda b: b.update(keys=[]),
        lambda b: b.pop("created_at"),
    ],
)
def test_invalid_genesis_is_rejected(mutate):
    body = genesis()
    mutate(body)
    with pytest.raises(EntryError):
        entries.validate(body, 0)


@pytest.mark.parametrize(
    "overrides",
    [
        {"space": ""},
        {"category": 3},
        {"content_hash": "A" * 64},
        {"valid_from": "2026-02-01", "valid_to": "2026-01-01"},
        {"valid_from": "2026-01-01", "valid_to": "2026-02-01T00:00:00.000000Z"},
        {"valid_from": "2026-02-30"},
        {"recorded_at": "2026-11-20 00:00:00"},
        {"recorded_at": "2026-02-30T00:00:00.000000Z"},
        {"writer": "root"},
        {"source": "rumor"},
        {"client": 5},
        {"derived_from": [3, 1]},
        {"derived_from": [1, 1]},
        {"derived_from": [5]},
        {"derived_from": [True]},
        {"kind": "approval"},
    ],
)
def test_invalid_memory_is_rejected(overrides):
    with pytest.raises(EntryError):
        entries.validate(memory(**overrides), 5)


def test_genesis_only_at_position_zero():
    with pytest.raises(EntryError):
        entries.validate(genesis(), 1)
    with pytest.raises(EntryError):
        entries.validate(memory(), 0)
    disguised = genesis()
    disguised["kind"] = "memory"
    with pytest.raises(EntryError):
        entries.validate(disguised, 0)

