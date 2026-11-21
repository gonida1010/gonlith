# 검증된 상태에서 만드는 파생 검색 색인(SQLite FTS5, BM25)과 완전 중복 확인용 정규화 해시 표 (docs/design.md §7.3, §9)
import hashlib
import re

from gonlith.tokens import normalize, tokenizer

SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS search_fts USING fts5(tokens, space UNINDEXED, tokenize = 'unicode61 remove_diacritics 0');
CREATE TABLE IF NOT EXISTS dedup (space TEXT NOT NULL, norm_hash TEXT NOT NULL, position INTEGER PRIMARY KEY);
CREATE INDEX IF NOT EXISTS dedup_lookup ON dedup (space, norm_hash);
CREATE TABLE IF NOT EXISTS index_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""
WHITESPACE = re.compile(r"\s+")


def dedup_hash(content):
    return hashlib.sha256(WHITESPACE.sub(" ", normalize(content)).strip().encode("utf-8")).hexdigest()


def _match_expression(tokens):
    return " OR ".join('"' + token.replace('"', '""') + '"' for token in dict.fromkeys(tokens))


class SearchIndex:
    def __init__(self, connection, tokenizer_name):
        self.connection = connection
        self.tokenizer_name = tokenizer_name
        self.tokenize = tokenizer(tokenizer_name)
        self.connection.executescript(SCHEMA)

    def _meta(self, key):
        row = self.connection.execute("SELECT value FROM index_meta WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None

    def _set_meta(self, cursor, key, value):
        cursor.execute(
            "INSERT INTO index_meta(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )

    def is_current(self, root_hex):
        return self._meta("tokenizer") == self.tokenizer_name and self._meta("root") == root_hex

    def rebuild(self, memories, read_content, root_hex):
        rows = [(position, read_content(position)) for position in sorted(memories)]
        cursor = self.connection.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        try:
            cursor.execute("DELETE FROM search_fts")
            cursor.execute("DELETE FROM dedup")
            for position, content in rows:
                if content is not None:
                    self._insert(cursor, position, memories[position]["space"], content)
            self._set_meta(cursor, "tokenizer", self.tokenizer_name)
            self._set_meta(cursor, "root", root_hex)
            cursor.execute("COMMIT")
        except BaseException:
            cursor.execute("ROLLBACK")
            raise

    def add(self, position, space, content, root_hex):
        cursor = self.connection.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        try:
            cursor.execute("DELETE FROM search_fts WHERE rowid = ?", (position,))
            cursor.execute("DELETE FROM dedup WHERE position = ?", (position,))
            self._insert(cursor, position, space, content)
            self._set_meta(cursor, "root", root_hex)
            cursor.execute("COMMIT")
        except BaseException:
            cursor.execute("ROLLBACK")
            raise

    def _insert(self, cursor, position, space, content):
        cursor.execute(
            "INSERT INTO search_fts(rowid, tokens, space) VALUES (?, ?, ?)",
            (position, " ".join(self.tokenize(content)), space),
        )
        cursor.execute(
            "INSERT INTO dedup(space, norm_hash, position) VALUES (?, ?, ?)", (space, dedup_hash(content), position)
        )

    def remove(self, position, root_hex):
        cursor = self.connection.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        try:
            cursor.execute("DELETE FROM search_fts WHERE rowid = ?", (position,))
            cursor.execute("DELETE FROM dedup WHERE position = ?", (position,))
            self._set_meta(cursor, "root", root_hex)
            cursor.execute("COMMIT")
        except BaseException:
            cursor.execute("ROLLBACK")
            raise

    def duplicates(self, space, content):
        rows = self.connection.execute(
            "SELECT position FROM dedup WHERE space = ? AND norm_hash = ? ORDER BY position",
            (space, dedup_hash(content)),
        )
        return [row[0] for row in rows]

    def candidates(self, query, spaces, limit):
        tokens = self.tokenize(query)
        if not tokens or not spaces:
            return []
        marks = ", ".join("?" for _ in spaces)
        rows = self.connection.execute(
            f"SELECT rowid, bm25(search_fts) FROM search_fts WHERE search_fts MATCH ? AND space IN ({marks}) "
            "ORDER BY bm25(search_fts) LIMIT ?",
            (_match_expression(tokens), *spaces, limit),
        )
        return [(position, -score) for position, score in rows]

    def indexed_positions(self):
        return {row[0] for row in self.connection.execute("SELECT rowid FROM search_fts")}
