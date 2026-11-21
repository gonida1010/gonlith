# 여러 프로세스가 같은 데이터 폴더에 동시에 기억을 추가해도 유실·위치 충돌 없이 검증되는지 확인하는 시험 (docs/decisions.md V3)
import multiprocessing

from gonlith.config import load_settings
from gonlith.store import Store
from gonlith.verify import read_content, replay

PROCESSES = 8
APPENDS_PER_PROCESS = 100


def _writer(home, worker):
    store = Store.open(home, load_settings(home))
    for index in range(APPENDS_PER_PROCESS):
        store.append_memory(
            f"worker {worker} memory {index}",
            space="default",
            category="fact",
            valid_from=None,
            valid_to=None,
            writer="agent",
            client=f"client-{worker}",
            session=f"session-{worker}",
            source="conversation",
            derived_from=[],
            tags=[],
        )
    store.close()


def test_concurrent_processes_append_without_loss(store, home):
    context = multiprocessing.get_context("spawn")
    workers = [context.Process(target=_writer, args=(home, worker)) for worker in range(PROCESSES)]
    for process in workers:
        process.start()
    for process in workers:
        process.join()
    assert [process.exitcode for process in workers] == [0] * PROCESSES
    state = replay(store)
    assert state.ok
    assert state.size == 1 + PROCESSES * APPENDS_PER_PROCESS
    contents = {read_content(state, store, position) for position in state.memories}
    expected = {f"worker {w} memory {i}" for w in range(PROCESSES) for i in range(APPENDS_PER_PROCESS)}
    assert contents == expected
