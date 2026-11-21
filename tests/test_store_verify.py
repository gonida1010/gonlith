# 저장소 init·추가·내용 분리와 재생 검증기가 변조 시나리오를 검출하는지 확인하는 시험 (docs/design.md §6, §7.2)
import base64
import sqlite3

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from typer.testing import CliRunner

from conftest import remember
from gonlith import entries
from gonlith.cli import app
from gonlith.store import StoreError
from gonlith.verify import extend, read_content, replay


def raw_connection(home):
    connection = sqlite3.connect(home / "gonlith.db", isolation_level=None)
    connection.execute("DROP TRIGGER IF EXISTS log_no_update")
    connection.execute("DROP TRIGGER IF EXISTS log_no_delete")
    return connection


def filled(store, count=4):
    for index in range(count):
        remember(store, f"기억 {index}: 사용자는 서울에 산다")
    return replay(store)


def test_initialize_once_and_recovery_key_matches_genesis(home, store):
    with pytest.raises(StoreError):
        store.initialize()
    state = replay(store)
    assert state.ok and state.size == 1
    assert state.origin.startswith(entries.ORIGIN_PREFIX)
    key = state.keys[0]
    assert key["rights"] == ["key"]
    assert sorted(path.name for path in home.iterdir() if not path.name.startswith("gonlith.db")) == []


def test_recovery_key_text_reproduces_public_key(home, monkeypatch):
    from gonlith.config import load_settings
    from gonlith.store import Store

    fresh = Store.open(home / "other", load_settings(home))
    text = fresh.initialize()
    state = replay(fresh)
    fresh.close()
    prefix, kind, name, key_id, data = text.split("+", 4)
    raw = base64.b64decode(data)
    public = Ed25519PrivateKey.from_private_bytes(raw[1:]).public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    assert (prefix, kind, raw[:1]) == ("PRIVATE", "KEY", entries.ED25519_NOTE_TYPE)
    assert name == state.keys[0]["name"]
    assert base64.b64encode(public).decode() == state.keys[0]["public_key"]
    assert key_id == entries.note_key_id(name, public).hex()


def test_append_and_read_back(store):
    first = remember(store, "사용자는 서울에 산다")
    second = remember(store, "이사했다: 부산", derived_from=[first], valid_from="2026-11-01")
    state = replay(store)
    assert state.ok and (first, second) == (1, 2)
    assert read_content(state, store, second) == "이사했다: 부산"
    assert state.memories[second]["derived_from"] == [first]


def test_append_rejects_bad_input(store):
    with pytest.raises(StoreError):
        remember(store, "")
    with pytest.raises(StoreError):
        remember(store, "\ud800")
    with pytest.raises(StoreError):
        remember(store, "x", derived_from=[0])
    with pytest.raises(entries.EntryError):
        remember(store, "x", source="rumor")
    assert replay(store).size == 1


def test_uninitialized_store_rejects_append(home):
    from gonlith.config import load_settings
    from gonlith.store import Store

    empty = Store.open(home / "empty", load_settings(home))
    with pytest.raises(StoreError):
        remember(empty, "x")
    assert not replay(empty).ok
    empty.close()


def test_triggers_block_update_and_delete(store):
    remember(store, "x")
    for statement in ("UPDATE log SET entry = x'00' WHERE position = 1", "DELETE FROM log WHERE position = 1"):
        with pytest.raises(sqlite3.IntegrityError):
            store.connection.execute(statement)


def tamper_modify(home, connection):
    entry = connection.execute("SELECT entry FROM log WHERE position = 2").fetchone()[0]
    connection.execute("UPDATE log SET entry = ? WHERE position = 2", (entry.replace(b"conversation", b"user_typed"),))


def tamper_insert(home, connection):
    rows = connection.execute("SELECT position, entry FROM log WHERE position >= 2 ORDER BY position DESC").fetchall()
    for position, entry in rows:
        connection.execute("UPDATE log SET position = ? WHERE position = ?", (position + 1, position))
    connection.execute("INSERT INTO log(position, entry) VALUES (2, (SELECT entry FROM log WHERE position = 1))")


def tamper_delete(home, connection):
    connection.execute("DELETE FROM log WHERE position = 2")


def tamper_reorder(home, connection):
    first = connection.execute("SELECT entry FROM log WHERE position = 1").fetchone()[0]
    second = connection.execute("SELECT entry FROM log WHERE position = 2").fetchone()[0]
    connection.execute("UPDATE log SET entry = ? WHERE position = 1", (second,))
    connection.execute("UPDATE log SET entry = ? WHERE position = 2", (first,))


def tamper_reorder_with_contents(home, connection):
    tamper_reorder(home, connection)
    one = connection.execute("SELECT salt, content FROM contents WHERE position = 1").fetchone()
    two = connection.execute("SELECT salt, content FROM contents WHERE position = 2").fetchone()
    connection.execute("UPDATE contents SET salt = ?, content = ? WHERE position = 1", two)
    connection.execute("UPDATE contents SET salt = ?, content = ? WHERE position = 2", one)


def tamper_truncate(home, connection):
    connection.execute("DELETE FROM log WHERE position = (SELECT MAX(position) FROM log)")


def tamper_genesis(home, connection):
    connection.execute("DELETE FROM log WHERE position = 0")


LOG_TAMPERS = [
    (tamper_modify, True),
    (tamper_insert, True),
    (tamper_delete, True),
    (tamper_reorder, True),
    (tamper_reorder_with_contents, False),
    (tamper_truncate, False),
    (tamper_genesis, True),
]


@pytest.mark.parametrize(("tamper", "self_detected"), LOG_TAMPERS, ids=lambda value: getattr(value, "__name__", ""))
def test_log_tampering_changes_trusted_checkpoint(home, store, tamper, self_detected):
    trusted = filled(store)
    trusted_size, trusted_root = trusted.size, trusted.root()
    connection = raw_connection(home)
    tamper(home, connection)
    connection.close()
    state = replay(store)
    assert state.ok is not self_detected
    if state.size >= trusted_size:
        assert state.root_at(trusted_size) != trusted_root
    else:
        assert state.size < trusted_size


def test_entries_after_first_bad_position_are_not_trusted(home, store):
    filled(store)
    connection = raw_connection(home)
    tamper_modify(home, connection)
    connection.close()
    state = replay(store)
    assert state.first_bad_position == 2
    assert sorted(state.memories) == [1]


def test_replay_rejects_derived_from_pointing_at_non_memory(home, store):
    remember(store, "x")
    body = entries.memory_body(
        space="default",
        category="fact",
        digest="0" * 64,
        valid_from=None,
        valid_to=None,
        recorded_at=entries.now_timestamp(),
        writer="agent",
        client=None,
        session="s",
        source="conversation",
        derived_from=[0],
    )
    connection = raw_connection(home)
    connection.execute("INSERT INTO log(position, entry) VALUES (2, ?)", (entries.wrap(body),))
    connection.close()
    state = replay(store)
    assert state.first_bad_position == 2 and 2 not in state.memories


def tamper_content_edit(connection):
    connection.execute("UPDATE contents SET content = ? WHERE position = 2", ("사용자는 부산에 산다".encode(),))


def tamper_content_swap(connection):
    one = connection.execute("SELECT salt, content FROM contents WHERE position = 1").fetchone()
    two = connection.execute("SELECT salt, content FROM contents WHERE position = 2").fetchone()
    connection.execute("UPDATE contents SET salt = ?, content = ? WHERE position = 1", two)
    connection.execute("UPDATE contents SET salt = ?, content = ? WHERE position = 2", one)


def tamper_content_delete(connection):
    connection.execute("DELETE FROM contents WHERE position = 2")


def tamper_salt_edit(connection):
    connection.execute("UPDATE contents SET salt = zeroblob(16) WHERE position = 2")


CONTENT_TAMPERS = [tamper_content_edit, tamper_content_swap, tamper_content_delete, tamper_salt_edit]


@pytest.mark.parametrize("tamper", CONTENT_TAMPERS, ids=lambda fn: fn.__name__)
def test_content_tampering_marks_memory_broken_without_touching_log(home, store, tamper):
    trusted = filled(store)
    connection = raw_connection(home)
    tamper(connection)
    connection.close()
    state = replay(store)
    assert state.memories[2]["integrity"] == "broken"
    assert read_content(state, store, 2) is None
    assert state.first_bad_position is None
    assert state.root() == trusted.root()
    assert read_content(state, store, 3) is not None


def test_content_tampering_after_replay_is_caught_on_read(home, store):
    state = filled(store)
    connection = raw_connection(home)
    tamper_content_edit(connection)
    connection.close()
    assert read_content(state, store, 2) is None
    assert state.memories[2]["integrity"] == "broken"


def test_appending_keeps_old_checkpoint_stable(store):
    state = filled(store)
    size, root = state.size, state.root()
    remember(store, "새 기억")
    grown = replay(store)
    assert grown.ok and grown.size == size + 1
    assert grown.root_at(size) == root and grown.root() != root


def test_incremental_extend_matches_full_replay(store):
    state = filled(store)
    remember(store, "추가 1")
    remember(store, "추가 2")
    extended = extend(state, store)
    full = replay(store)
    assert extended.size == full.size and extended.root() == full.root()
    assert sorted(extended.memories) == sorted(full.memories)


def test_extend_falls_back_to_full_replay_when_tail_changed(home, store):
    state = filled(store)
    connection = raw_connection(home)
    tamper_truncate(home, connection)
    connection.close()
    refreshed = extend(state, store)
    assert refreshed is not state and refreshed.size == state.size - 1


def test_cli_init_and_verify(home):
    runner = CliRunner()
    created = runner.invoke(app, ["init"])
    assert created.exit_code == 0 and created.stdout.startswith("PRIVATE+KEY+gonlith.invalid/")
    again = runner.invoke(app, ["init"])
    assert again.exit_code == 1
    checked = runner.invoke(app, ["verify", "--json"])
    assert checked.exit_code == 0 and '"ok": true' in checked.stdout
    connection = raw_connection(home)
    connection.execute("UPDATE log SET entry = x'00' WHERE position = 0")
    connection.close()
    broken = runner.invoke(app, ["verify"])
    assert broken.exit_code == 1 and "PROBLEMS FOUND" in broken.stdout
