# 2-gram 토크나이저의 한 글자 단어·정규화(NFKC·대소문자)·영숫자 처리를 확인하는 시험 (docs/design.md §9)
from gonlith.tokens import bigram_tokens


def test_single_syllable_hangul_word_is_kept():
    assert bigram_tokens("밥") == ["밥"]


def test_hangul_run_becomes_overlapping_bigrams():
    assert bigram_tokens("서울에") == ["서울", "울에"]


def test_case_and_width_are_normalized():
    assert bigram_tokens("Ｐｙｔｈｏｎ") == bigram_tokens("python") == ["python"]


def test_mixed_word_splits_latin_and_hangul_parts():
    assert bigram_tokens("uv를") == ["uv", "를"]
