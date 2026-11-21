# 서비스 계층의 저장·검색·중복 거부·휴지통·다중 프로세스 반영·색인 복구·변조 차단을 확인하는 시험 (docs/design.md §7, §9)
import sqlite3

import pytest

from gonlith.config import load_settings
from gonlith.service import MemoryService, ServiceError


@pytest.fixture
def settings(home):
    return load_settings(home)


@pytest.fixture
def service(home, settings):
    opened = MemoryService(home, settings, session="s1")
    yield opened
    opened.close()


def save(service, content, **overrides):
    fields = dict(category="fact", source="conversation", client="test")
    fields.update(overrides)
    return service.remember(content, **fields)


def ids(found):
    return [memory["id"] for memory in found["results"]]


def test_first_run_creates_store_and_finds_two_syllable_korean_word(service):
    first = save(service, "사용자는 서울에 산다")
    save(service, "The user prefers dark roast coffee")
    assert ids(service.search("서울", limit=5)) == [first["id"]]
    assert ids(service.search("coffee", limit=5)) != []
    assert service.status()["active"] == 2


def test_identical_content_in_same_space_is_not_saved_twice(service):
    first = save(service, "사용자는 채식을 한다")
    again = save(service, "  사용자는   채식을 한다 ")
    other_space = save(service, "사용자는 채식을 한다", space="project-a")
    assert again == {"id": first["id"], "duplicate": True, "space": "personal"}
    assert other_space["duplicate"] is False


def test_forget_moves_to_trash_and_hides_from_search(service):
    memory = save(service, "회의는 매주 화요일")
    assert service.forget(memory["id"], client="test")["status"] == "archived"
    assert ids(service.search("화요일", limit=5)) == []
    with pytest.raises(ServiceError):
        service.forget(memory["id"], client="test")
    assert save(service, "회의는 매주 화요일")["duplicate"] is False


def test_spaces_scope_search_to_current_and_personal(home, settings):
    project = MemoryService(home, settings, session="s2", default_space="project-a")
    personal_fact = save(project, "나는 파이썬을 쓴다", space="personal")
    project_fact = save(project, "이 프로젝트는 파이썬 uv를 쓴다")
    other = save(project, "다른 프로젝트도 파이썬을 쓴다", space="project-b")
    found = ids(project.search("파이썬", limit=10))
    project.close()
    assert set(found) == {personal_fact["id"], project_fact["id"]}
    assert other["id"] not in found


def test_writes_from_another_process_are_picked_up(home, settings, service):
    other = MemoryService(home, settings, session="s3")
    written = save(other, "다른 클라이언트가 저장한 기억")
    other.close()
    assert ids(service.search("클라이언트", limit=5)) == [written["id"]]


def test_external_source_is_marked_external(service):
    memory = save(service, "웹에서 가져온 문장", source="web")
    found = service.search("문장", limit=5)["results"][0]
    assert memory["origin"] == "external" and found["origin"] == "external"


def test_damaged_index_is_rebuilt_on_start(home, settings, service):
    memory = save(service, "색인이 지워져도 다시 찾는다")
    service.close()
    connection = sqlite3.connect(home / "gonlith.db", isolation_level=None)
    connection.execute("DELETE FROM search_fts")
    connection.close()
    reopened = MemoryService(home, settings, session="s4")
    assert ids(reopened.search("색인", limit=5)) == [memory["id"]]
    reopened.close()


def test_tampered_content_is_withheld_with_warning(home, service):
    memory = save(service, "변조되면 나오지 않는다")
    connection = sqlite3.connect(home / "gonlith.db", isolation_level=None)
    connection.execute("UPDATE contents SET content = ? WHERE position = ?", ("변조된 내용 나오지".encode(), memory["id"]))
    connection.close()
    found = service.search("나오지", limit=5)
    assert found["results"] == [] and any("integrity" in warning for warning in found["warnings"])


def test_index_holds_exactly_the_active_memories(home, settings, service):
    kept = save(service, "남는 기억")
    trashed = save(service, "버리는 기억")
    service.forget(trashed["id"], client="test")
    assert service.index.indexed_positions() == {kept["id"]}
    service.close()
    reopened = MemoryService(home, settings, session="s5")
    assert reopened.index.indexed_positions() == {kept["id"]}
    reopened.close()


def test_stale_index_row_for_trashed_memory_is_not_returned(service):
    memory = save(service, "낡은 색인 행 시험")
    service.forget(memory["id"], client="test")
    service.store.connection.execute(
        "INSERT INTO search_fts(rowid, tokens, space) VALUES (?, ?, ?)", (memory["id"], "낡은 색인", "personal")
    )
    assert ids(service.search("낡은", limit=5)) == []


def test_trash_written_by_another_process_reaches_the_index(home, settings, service):
    from gonlith.store import Store

    memory = save(service, "다른 곳에서 버린 기억")
    other = Store.open(home, settings)
    other.append_archive(memory["id"], writer="agent", client="other", session="s6", reason=None)
    other.close()
    service.refresh()
    assert memory["id"] not in service.index.indexed_positions()
