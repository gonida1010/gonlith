# 시험마다 임시 데이터 폴더를 GONLITH_HOME으로 지정해 사용자 홈에 흔적을 남기지 않게 하는 공통 준비물
import pytest

from gonlith.config import HOME_ENV, load_settings
from gonlith.store import Store


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv(HOME_ENV, str(tmp_path))
    return tmp_path


@pytest.fixture
def store(home):
    opened = Store.open(home, load_settings(home))
    opened.initialize()
    yield opened
    opened.close()


def remember(store, content, **overrides):
    fields = dict(
        space="default",
        category="fact",
        valid_from=None,
        valid_to=None,
        writer="agent",
        client="test-client",
        session="session-1",
        source="conversation",
        derived_from=[],
    )
    fields.update(overrides)
    return store.append_memory(content, **fields)
