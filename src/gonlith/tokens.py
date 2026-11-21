# 검색 색인용 토크나이저: 한글 문자 2-gram(기본, 추가 설치 없음), kiwi 형태소(선택), 둘의 혼합 (docs/design.md §9)
import re
import unicodedata
from functools import lru_cache

HANGUL_RUN = re.compile(r"[가-힣]+")
WORD_RUN = re.compile(r"[^\W_]+", re.UNICODE)
KIWI_CONTENT_TAGS = ("NNG", "NNP", "NNB", "NR", "NP", "VV", "VA", "XR", "SL", "SH", "SN", "MAG")


def normalize(text):
    return unicodedata.normalize("NFKC", text).casefold()


def _hangul_bigrams(run):
    if len(run) == 1:
        return [run]
    return [run[index : index + 2] for index in range(len(run) - 1)]


def bigram_tokens(text):
    tokens = []
    for word in WORD_RUN.findall(normalize(text)):
        position = 0
        for match in HANGUL_RUN.finditer(word):
            if match.start() > position:
                tokens.append(word[position : match.start()])
            tokens.extend(_hangul_bigrams(match.group()))
            position = match.end()
        if position < len(word):
            tokens.append(word[position:])
    return tokens


@lru_cache(maxsize=1)
def _kiwi():
    from kiwipiepy import Kiwi

    return Kiwi()


def kiwi_tokens(text):
    return [
        normalize(token.form)
        for token in _kiwi().tokenize(unicodedata.normalize("NFKC", text))
        if token.tag.startswith(KIWI_CONTENT_TAGS)
    ]


def hybrid_tokens(text):
    return kiwi_tokens(text) + bigram_tokens(text)


TOKENIZERS = {"bigram": bigram_tokens, "kiwi": kiwi_tokens, "hybrid": hybrid_tokens}


def tokenizer(name):
    if name not in TOKENIZERS:
        raise ValueError(f"unknown tokenizer {name!r}, expected one of {sorted(TOKENIZERS)}")
    return TOKENIZERS[name]
