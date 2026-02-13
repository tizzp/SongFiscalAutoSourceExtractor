from __future__ import annotations

from typing import Any

from opencc import OpenCC


class TextNormalizer:
    def __init__(self, synonym_lexicon: dict[str, Any]):
        self.converter = OpenCC("t2s")
        self.t2s_map = synonym_lexicon.get("traditional_to_simplified", {})

    def normalize(self, text: str) -> str:
        s = self.converter.convert(text)
        for traditional, simplified in self.t2s_map.items():
            s = s.replace(traditional, simplified)
        return s

    def normalize_keyword(self, keyword: str) -> str:
        return self.normalize(keyword)
