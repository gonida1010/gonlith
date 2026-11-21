# RFC 6962 §2.1 Merkle 트리 해시: 잎·내부 노드 해시와 추가 전용 프런티어로 트리 루트를 계산한다
import hashlib

LEAF_PREFIX = b"\x00"
NODE_PREFIX = b"\x01"


def leaf_hash(data):
    return hashlib.sha256(LEAF_PREFIX + data).digest()


def node_hash(left, right):
    return hashlib.sha256(NODE_PREFIX + left + right).digest()


def empty_root():
    return hashlib.sha256(b"").digest()


class Frontier:
    def __init__(self):
        self.size = 0
        self._subtrees = []

    def append(self, leaf):
        digest, height = leaf, 0
        while self._subtrees and self._subtrees[-1][0] == height:
            digest = node_hash(self._subtrees.pop()[1], digest)
            height += 1
        self._subtrees.append((height, digest))
        self.size += 1

    def root(self):
        if not self._subtrees:
            return empty_root()
        digest = self._subtrees[-1][1]
        for _, left in reversed(self._subtrees[:-1]):
            digest = node_hash(left, digest)
        return digest
