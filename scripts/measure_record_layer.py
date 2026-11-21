# 기록 계층(S1) 측정: 전체·증분 재생 비용과 다중 프로세스 동시 쓰기 지연을 임시 데이터 폴더에서 재현 가능하게 잰다 (docs/design.md §11)
import argparse
import json
import multiprocessing
import platform
import sqlite3
import statistics
import sys
import tempfile
import time
from pathlib import Path

from gonlith.config import load_settings
from gonlith.store import Store
from gonlith.verify import extend, replay

FIELDS = dict(
    space="default",
    category="fact",
    valid_from=None,
    valid_to=None,
    writer="agent",
    client="measure",
    session="measure",
    source="conversation",
    derived_from=[],
    tags=[],
)


def _fill(store, count):
    for index in range(count):
        store.append_memory(f"측정용 기억 {index}: 사용자는 서울에 산다", **FIELDS)


def measure_replay(size, repeats, incremental_batch):
    with tempfile.TemporaryDirectory() as home:
        store = Store.open(home, load_settings(home))
        store.initialize()
        _fill(store, size)
        full = []
        for _ in range(repeats):
            started = time.perf_counter()
            state = replay(store)
            full.append(time.perf_counter() - started)
            assert state.ok and state.size == size + 1
        _fill(store, incremental_batch)
        started = time.perf_counter()
        extended = extend(state, store)
        incremental = time.perf_counter() - started
        assert extended.ok and extended.size == size + 1 + incremental_batch
        database_bytes = sum(path.stat().st_size for path in Path(home).iterdir())
        store.close()
    return {
        "memories": size,
        "full_replay_median_s": round(statistics.median(full), 4),
        "full_replay_max_s": round(max(full), 4),
        "incremental_batch": incremental_batch,
        "incremental_s": round(incremental, 4),
        "database_bytes": database_bytes,
    }


def _writer(home, appends, queue):
    store = Store.open(home, load_settings(home))
    latencies = []
    for index in range(appends):
        started = time.perf_counter()
        store.append_memory(f"동시 쓰기 {index}", **FIELDS)
        latencies.append(time.perf_counter() - started)
    store.close()
    queue.put(latencies)


def measure_concurrency(processes, appends):
    context = multiprocessing.get_context("spawn")
    with tempfile.TemporaryDirectory() as home:
        store = Store.open(home, load_settings(home))
        store.initialize()
        queue = context.Queue()
        workers = [context.Process(target=_writer, args=(home, appends, queue)) for _ in range(processes)]
        started = time.perf_counter()
        for worker in workers:
            worker.start()
        latencies = [value for _ in workers for value in queue.get()]
        for worker in workers:
            worker.join()
        elapsed = time.perf_counter() - started
        state = replay(store)
        store.close()
    ordered = sorted(latencies)
    return {
        "processes": processes,
        "appends_per_process": appends,
        "lost": processes * appends + 1 - state.size,
        "verified": state.ok,
        "append_p50_ms": round(ordered[len(ordered) // 2] * 1000, 3),
        "append_p99_ms": round(ordered[int(len(ordered) * 0.99) - 1] * 1000, 3),
        "append_max_ms": round(ordered[-1] * 1000, 3),
        "wall_s": round(elapsed, 3),
        "failed_workers": sum(worker.exitcode != 0 for worker in workers),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", type=int, nargs="+", required=True)
    parser.add_argument("--repeats", type=int, required=True)
    parser.add_argument("--incremental-batch", type=int, required=True)
    parser.add_argument("--processes", type=int, nargs="+", required=True)
    parser.add_argument("--appends", type=int, required=True)
    args = parser.parse_args()
    report = {
        "environment": {
            "python": sys.version.split()[0],
            "sqlite": sqlite3.sqlite_version,
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "replay": [measure_replay(size, args.repeats, args.incremental_batch) for size in args.sizes],
        "concurrency": [measure_concurrency(count, args.appends) for count in args.processes],
    }
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
