# Gonlith SQLite 저장소: init(복구 키·genesis), 추가 전용 로그, 로그와 분리된 내용 저장 (docs/format.md §6)
import base64
import os
import sqlite3
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, PublicFormat

from gonlith import entries

SCHEMA = """
CREATE TABLE IF NOT EXISTS log (position INTEGER PRIMARY KEY, entry BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS contents (position INTEGER PRIMARY KEY, salt BLOB NOT NULL, content BLOB NOT NULL);
CREATE TRIGGER IF NOT EXISTS log_no_update BEFORE UPDATE ON log BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS log_no_delete BEFORE DELETE ON log BEGIN SELECT RAISE(ABORT, 'append-only'); END;
"""


class StoreError(RuntimeError):
    pass


def recovery_key_text(name, private_seed, public_key):
    key_id = entries.note_key_id(name, public_key).hex()
    encoded = base64.b64encode(entries.ED25519_NOTE_TYPE + private_seed).decode("ascii")
    return f"PRIVATE+KEY+{name}+{key_id}+{encoded}"


class Store:
    def __init__(self, path, busy_timeout_seconds):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, timeout=busy_timeout_seconds, isolation_level=None)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA secure_delete=ON")
        self.connection.executescript(SCHEMA)

    @classmethod
    def open(cls, home, settings):
        storage = settings["storage"]
        return cls(Path(home) / storage["database_file"], storage["busy_timeout_seconds"])

    def close(self):
        self.connection.close()

    def _transaction(self, work):
        cursor = self.connection.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        try:
            result = work(cursor)
            cursor.execute("COMMIT")
        except BaseException:
            cursor.execute("ROLLBACK")
            raise
        return result

    def initialize(self):
        private_key = Ed25519PrivateKey.generate()
        seed = private_key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
        public_key = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        origin = entries.ORIGIN_PREFIX + os.urandom(entries.ORIGIN_RANDOM_BYTES).hex()
        body = entries.genesis_body(origin, public_key, entries.now_timestamp())
        entries.validate(body, 0)

        def work(cursor):
            if cursor.execute("SELECT 1 FROM log LIMIT 1").fetchone():
                raise StoreError("log is already initialized")
            cursor.execute("INSERT INTO log(position, entry) VALUES (0, ?)", (entries.wrap(body),))

        self._transaction(work)
        return recovery_key_text(body["keys"][0]["name"], seed, public_key)

    def append_memory(self, content, *, space, category, valid_from, valid_to, writer, client, session, source, derived_from):
        if not isinstance(content, str) or content == "":
            raise StoreError("content must be a non-empty string")
        try:
            content_bytes = content.encode("utf-8")
        except UnicodeEncodeError as error:
            raise StoreError(f"content is not valid Unicode: {error}") from error
        salt = os.urandom(entries.SALT_BYTES)
        body = entries.memory_body(
            space=space,
            category=category,
            digest=entries.content_hash(salt, content_bytes),
            valid_from=valid_from,
            valid_to=valid_to,
            recorded_at=entries.now_timestamp(),
            writer=writer,
            client=client,
            session=session,
            source=source,
            derived_from=derived_from,
        )

        def work(cursor):
            position = cursor.execute("SELECT COALESCE(MAX(position) + 1, 0) FROM log").fetchone()[0]
            if position == 0:
                raise StoreError("log is not initialized")
            entries.validate(body, position)
            for target in body["derived_from"]:
                row = cursor.execute("SELECT entry FROM log WHERE position = ?", (target,)).fetchone()
                if row is None or entries.unwrap(row[0]).get("kind") != "memory":
                    raise StoreError(f"derived_from {target} is not a memory")
            cursor.execute("INSERT INTO log(position, entry) VALUES (?, ?)", (position, entries.wrap(body)))
            cursor.execute(
                "INSERT INTO contents(position, salt, content) VALUES (?, ?, ?)", (position, salt, content_bytes)
            )
            return position

        return self._transaction(work)

    def entries_from(self, start):
        return self.connection.execute("SELECT position, entry FROM log WHERE position >= ? ORDER BY position", (start,))

    def entry_at(self, position):
        row = self.connection.execute("SELECT entry FROM log WHERE position = ?", (position,)).fetchone()
        return row[0] if row else None

    def content_at(self, position):
        return self.connection.execute("SELECT salt, content FROM contents WHERE position = ?", (position,)).fetchone()

    def data_version(self):
        return self.connection.execute("PRAGMA data_version").fetchone()[0]
