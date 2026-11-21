# RFC 6962 Merkle 루트 계산을 공인 시험 벡터와 재귀 정의로 검증하는 시험
from hypothesis import given
from hypothesis import strategies as st

from gonlith.merkle import Frontier, empty_root, leaf_hash, node_hash

VECTOR_SOURCE = "github.com/transparency-dev/merkle testonly/constants.go @ 75a6539d7b48af0d529236f24487d2814fd1dca7"
LEAF_INPUTS = [
    "",
    "00",
    "10",
    "2021",
    "3031",
    "40414243",
    "5051525354555657",
    "606162636465666768696a6b6c6d6e6f",
]
ROOT_HASHES = [
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "6e340b9cffb37a989ca544e6bb780a2c78901d3fb33738768511a30617afa01d",
    "fac54203e7cc696cf0dfcb42c92a1d9dbaf70ad9e621f4bd8d98662f00e3c125",
    "aeb6bcfe274b70a14fb067a5e5578264db0fa9b51af5e0ba159158f329e06e77",
    "d37ee418976dd95753c1c73862b9398fa2a2cf9b4ff0fdfe8b30cd95209614b7",
    "4e3bbb1f7b478dcfe71fb631631519a3bca12c9aefca1612bfce4c13a86264d4",
    "76e67dadbcdf1e10e1b74ddc608abd2f98dfb16fbce75277b5232a127f2087ef",
    "ddb89be403809e325750d3d263cd78929c2942b7942a34b77e122c9594a74c8c",
    "5dc9da79a70659a9ad559cb701ded9a2ab9d823aad2f4960cfe370eff4604328",
]


def reference_root(leaves):
    if not leaves:
        return empty_root()
    if len(leaves) == 1:
        return leaves[0]
    split = 1 << ((len(leaves) - 1).bit_length() - 1)
    return node_hash(reference_root(leaves[:split]), reference_root(leaves[split:]))


def test_roots_match_published_vectors():
    frontier = Frontier()
    assert frontier.root().hex() == ROOT_HASHES[0]
    for size, data in enumerate(LEAF_INPUTS, start=1):
        frontier.append(leaf_hash(bytes.fromhex(data)))
        assert frontier.size == size
        assert frontier.root().hex() == ROOT_HASHES[size]


@given(st.lists(st.binary(max_size=8), max_size=70))
def test_frontier_matches_recursive_definition(items):
    leaves = [leaf_hash(item) for item in items]
    frontier = Frontier()
    for leaf in leaves:
        frontier.append(leaf)
    assert frontier.root() == reference_root(leaves)


@given(st.lists(st.binary(max_size=8), min_size=1, max_size=40), st.data())
def test_any_changed_leaf_changes_root(items, data):
    index = data.draw(st.integers(0, len(items) - 1))
    changed = list(items)
    changed[index] = items[index] + b"x"
    original = [leaf_hash(item) for item in items]
    tampered = [leaf_hash(item) for item in changed]
    assert reference_root(original) != reference_root(tampered)
