# 저장소·재생 검증 상태·검색 색인을 묶어 기억 저장·검색·휴지통 이동을 제공하는 서비스 계층 (docs/design.md §7, §9, §11)
from collections import Counter

from gonlith import entries
from gonlith.index import SearchIndex
from gonlith.store import Store, StoreError
from gonlith.verify import extend, read_content, replay


class ServiceError(ValueError):
    pass


class MemoryService:
    def __init__(self, home, settings, *, session, default_space=None):
        self.settings = settings
        self.session = session
        self.personal_space = settings["spaces"]["personal"]
        self.default_space = default_space or self.personal_space
        self.store = Store.open(home, settings)
        if self.store.entry_at(0) is None:
            try:
                self.store.initialize()
            except StoreError:
                pass
        self.state = replay(self.store)
        self.index = SearchIndex(self.store.connection, settings["search"]["tokenizer"])
        self._version = self.store.data_version()
        self._ensure_index()

    def close(self):
        self.store.close()

    def _root(self):
        return self.state.root().hex()

    def _active(self):
        return {
            position: memory
            for position, memory in self.state.memories.items()
            if memory["status"] == "active" and memory["integrity"] == "ok"
        }

    def _ensure_index(self):
        active = self._active()
        if not self.index.is_current(self._root()) or self.index.indexed_positions() != set(active):
            self.index.rebuild(active, lambda position: read_content(self.state, self.store, position), self._root())

    def _advance(self):
        previous = self.state.size
        self.state = extend(self.state, self.store)
        if self.state.size < previous or self.state.first_bad_position is not None:
            self._ensure_index()
            return
        for position in range(previous, self.state.size):
            memory = self.state.memories.get(position)
            if memory is not None and memory["status"] == "active":
                content = read_content(self.state, self.store, position)
                if content is not None:
                    self.index.add(position, memory["space"], content, self._root())
            if position in self.state.archives:
                self.index.remove(self.state.archives[position], self._root())

    def refresh(self):
        version = self.store.data_version()
        if version != self._version:
            self._version = version
            self._advance()

    def remember(self, content, *, category, space=None, tags=(), valid_from=None, valid_to=None, source, client, writer="agent"):
        self.refresh()
        space = space or self.default_space
        existing = [position for position in self.index.duplicates(space, content) if position in self._active()]
        if existing:
            return {"id": existing[0], "duplicate": True, "space": space}
        try:
            position = self.store.append_memory(
                content,
                space=space,
                category=category,
                valid_from=valid_from,
                valid_to=valid_to,
                writer=writer,
                client=client,
                session=self.session,
                source=source,
                derived_from=[],
                tags=list(tags),
            )
        except (StoreError, entries.EntryError) as error:
            raise ServiceError(str(error)) from error
        self._advance()
        return {"id": position, "duplicate": False, "space": space, "origin": entries.origin_of(source)}

    def search(self, query, *, spaces=None, limit):
        self.refresh()
        scope = list(dict.fromkeys(spaces or [self.default_space, self.personal_space]))
        results, warnings = [], []
        for position, score in self.index.candidates(query, scope, limit):
            memory = self.state.memories.get(position)
            if memory is None or memory["status"] != "active":
                continue
            content = read_content(self.state, self.store, position)
            if content is None:
                warnings.append(f"memory {position} failed its integrity check and was withheld")
                continue
            results.append(dict(memory, id=position, content=content, score=score))
        if not self.state.ok:
            warnings.append(f"store integrity problems: {len(self.state.problems)} (run `gonlith verify`)")
        return {"results": results, "warnings": warnings, "spaces": scope}

    def forget(self, memory_id, *, client, reason=None, writer="agent"):
        self.refresh()
        memory = self.state.memories.get(memory_id)
        if memory is None or memory["status"] != "active":
            raise ServiceError(f"{memory_id} is not an active memory")
        self.store.append_archive(memory_id, writer=writer, client=client, session=self.session, reason=reason)
        self._advance()
        return {"id": memory_id, "status": "archived"}

    def status(self):
        self.refresh()
        memories = self.state.memories.values()
        return {
            "entries": self.state.size,
            "active": sum(m["status"] == "active" for m in memories),
            "archived": sum(m["status"] == "archived" for m in memories),
            "spaces": dict(Counter(m["space"] for m in memories if m["status"] == "active")),
            "integrity_ok": self.state.ok,
            "problems": len(self.state.problems),
        }
