# 어휘 검색 방식(2-gram·kiwi·혼합과 FTS5 trigram·기본 단어 분할 기준선)을 평가셋으로 비교해 Recall@k·MRR·지연·색인 시간을 잰다 (docs/design.md §9, §17)
import argparse
import json
import platform
import re
import sqlite3
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

from gonlith.index import SearchIndex
from gonlith.tokens import normalize

WORD = re.compile(r"[^\W_]+", re.UNICODE)


def gonlith_method(name):
    def build(memories):
        connection = sqlite3.connect(":memory:", isolation_level=None)
        index = SearchIndex(connection, name)
        state = {position: {"space": item["space"]} for position, item in enumerate(memories)}
        started = time.perf_counter()
        index.rebuild(state, lambda position: memories[position]["content"], "eval")
        build_seconds = time.perf_counter() - started
        spaces = sorted({item["space"] for item in memories})
        return (lambda query, k: [position for position, _ in index.candidates(query, spaces, k)]), build_seconds

    return build


def fts_baseline(tokenizer, min_chars):
    def build(memories):
        connection = sqlite3.connect(":memory:", isolation_level=None)
        connection.execute(f"CREATE VIRTUAL TABLE t USING fts5(body, tokenize = '{tokenizer}')")
        started = time.perf_counter()
        connection.executemany("INSERT INTO t(rowid, body) VALUES (?, ?)", [(i, m["content"]) for i, m in enumerate(memories)])
        build_seconds = time.perf_counter() - started

        def search(query, k):
            words = [w for w in WORD.findall(normalize(query)) if len(w) >= min_chars]
            if not words:
                return []
            expression = " OR ".join('"' + w.replace('"', '""') + '"' for w in words)
            rows = connection.execute("SELECT rowid FROM t WHERE t MATCH ? ORDER BY bm25(t) LIMIT ?", (expression, k))
            return [row[0] for row in rows]

        return search, build_seconds

    return build


METHODS = {
    "bigram": gonlith_method("bigram"),
    "kiwi": gonlith_method("kiwi"),
    "hybrid": gonlith_method("hybrid"),
    "fts5_trigram": fts_baseline("trigram", 3),
    "fts5_unicode61_words": fts_baseline("unicode61", 1),
}


def evaluate(dataset, method, ks):
    memories = dataset["memories"]
    position_of = {item["id"]: position for position, item in enumerate(memories)}
    search, build_seconds = METHODS[method](memories)
    max_k = max(ks)
    per_query, latencies = [], []
    for query in dataset["queries"]:
        started = time.perf_counter()
        ranked = search(query["q"], max_k)
        latencies.append(time.perf_counter() - started)
        relevant = {position_of[r] for r in query["relevant"]}
        first_hit = next((rank for rank, position in enumerate(ranked, start=1) if position in relevant), None)
        per_query.append(
            {
                "type": query["type"],
                "recall": {k: len(relevant & set(ranked[:k])) / len(relevant) for k in ks},
                "rr": 1 / first_hit if first_hit else 0.0,
            }
        )
    by_type = defaultdict(list)
    for row in per_query:
        by_type[row["type"]].append(row["recall"][5 if 5 in ks else max_k])
    return {
        "method": method,
        "recall": {f"@{k}": round(statistics.mean(r["recall"][k] for r in per_query), 4) for k in ks},
        "mrr": round(statistics.mean(r["rr"] for r in per_query), 4),
        "recall_at5_by_type": {t: round(statistics.mean(v), 4) for t, v in sorted(by_type.items())},
        "index_build_ms": round(build_seconds * 1000, 2),
        "query_p50_ms": round(statistics.median(latencies) * 1000, 3),
        "query_max_ms": round(max(latencies) * 1000, 3),
    }


def _jsonl(path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_beir(root, split):
    corpus = _jsonl(root / "corpus.jsonl")
    queries = {row["_id"]: row["text"] for row in _jsonl(root / "queries.jsonl")}
    relevant = defaultdict(list)
    for row in _jsonl(root / "qrels" / f"{split}.jsonl"):
        if row["score"] > 0:
            relevant[row["query-id"]].append(row["corpus-id"])
    return {
        "version": f"beir:{root.parent.name}@{root.name}:{split}",
        "memories": [{"id": doc["_id"], "space": "eval", "content": doc["text"]} for doc in corpus],
        "queries": [{"q": queries[qid], "relevant": ids, "type": "beir"} for qid, ids in relevant.items() if qid in queries],
    }


def load_belebele(path):
    rows = _jsonl(path)
    passages = {}
    for row in rows:
        passages.setdefault(row["flores_passage"], f"p{len(passages)}")
    return {
        "version": f"belebele:{path.name}",
        "memories": [{"id": pid, "space": "eval", "content": text} for text, pid in passages.items()],
        "queries": [{"q": row["question"], "relevant": [passages[row["flores_passage"]]], "type": "belebele"} for row in rows],
    }


def load_dataset(path, kind, split):
    if kind == "beir":
        return load_beir(path, split)
    if kind == "belebele":
        return load_belebele(path)
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--format", choices=("gonlith", "beir", "belebele"), required=True)
    parser.add_argument("--split", help="qrels split for beir datasets")
    parser.add_argument("--methods", nargs="+", choices=sorted(METHODS), required=True)
    parser.add_argument("--ks", type=int, nargs="+", required=True)
    args = parser.parse_args()
    dataset = load_dataset(args.dataset, args.format, args.split)
    report = {
        "dataset": dataset["version"],
        "memories": len(dataset["memories"]),
        "queries": len(dataset["queries"]),
        "environment": {"python": sys.version.split()[0], "sqlite": sqlite3.sqlite_version, "platform": platform.platform()},
        "results": [evaluate(dataset, method, args.ks) for method in args.methods],
    }
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
