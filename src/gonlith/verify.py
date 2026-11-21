# 로그를 처음부터 재생해 엄격 판독·연속 위치·Merkle 루트·내용 해시를 검증하고 기억별 검증 상태를 만드는 재생기 (docs/design.md §7.2)
import base64
from dataclasses import dataclass, field

from gonlith import entries
from gonlith.merkle import Frontier, leaf_hash


@dataclass
class Problem:
    position: int
    reason: str


@dataclass
class VerifiedLog:
    origin: str | None = None
    leaf_hashes: list = field(default_factory=list)
    frontier: Frontier = field(default_factory=Frontier)
    memories: dict = field(default_factory=dict)
    problems: list = field(default_factory=list)
    first_bad_position: int | None = None

    @property
    def size(self):
        return self.frontier.size

    @property
    def ok(self):
        return not self.problems

    def root(self):
        return self.frontier.root()

    def root_at(self, size):
        if not 0 <= size <= self.size:
            raise ValueError(f"size {size} outside 0..{self.size}")
        prefix = Frontier()
        for digest in self.leaf_hashes[:size]:
            prefix.append(digest)
        return prefix.root()

    def checkpoint(self):
        return checkpoint_text(self.origin, self.size, self.root())


def checkpoint_text(origin, size, root):
    return f"{origin}\n{size}\n{base64.b64encode(root).decode('ascii')}\n"


def _fail(state, position, reason):
    state.problems.append(Problem(position, reason))
    if state.first_bad_position is None:
        state.first_bad_position = position


def _content_ok(store, position, digest):
    row = store.content_at(position)
    return row is not None and entries.content_hash(row[0], row[1]) == digest


def _apply(state, store, position, entry):
    state.leaf_hashes.append(leaf_hash(entry))
    state.frontier.append(state.leaf_hashes[-1])
    if state.first_bad_position is not None:
        return
    try:
        body = entries.unwrap(entry)
        entries.validate(body, position)
    except entries.EntryError as error:
        _fail(state, position, f"invalid entry: {error}")
        return
    if body["kind"] == "genesis":
        state.origin = body["origin"]
        return
    for target in body["derived_from"]:
        if target not in state.memories:
            _fail(state, position, f"derived_from {target} is not a memory")
            return
    memory = dict(body, position=position, integrity="ok")
    if not _content_ok(store, position, body["content_hash"]):
        memory["integrity"] = "broken"
        state.problems.append(Problem(position, "content missing or hash mismatch"))
    state.memories[position] = memory


def _replay_rows(state, store, start):
    expected = start
    for position, entry in store.entries_from(start):
        if position != expected:
            _fail(state, expected, f"position gap: found {position}")
            expected = position
        _apply(state, store, position, entry)
        expected += 1


def replay(store):
    state = VerifiedLog()
    _replay_rows(state, store, 0)
    if state.size == 0:
        _fail(state, 0, "log is empty")
    return state


def extend(state, store):
    if state.size:
        current = store.entry_at(state.size - 1)
        if current is None or leaf_hash(current) != state.leaf_hashes[-1]:
            return replay(store)
    _replay_rows(state, store, state.size)
    return state


def read_content(state, store, position):
    memory = state.memories.get(position)
    if memory is None or memory["integrity"] != "ok":
        return None
    row = store.content_at(position)
    if row is None or entries.content_hash(row[0], row[1]) != memory["content_hash"]:
        memory["integrity"] = "broken"
        return None
    return row[1].decode("utf-8")
