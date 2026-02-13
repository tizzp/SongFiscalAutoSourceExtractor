from dataclasses import asdict, dataclass

from bs4 import BeautifulSoup


@dataclass
class ParsedParagraph:
    section_path: str
    paragraph_index: int
    text: str

    def to_dict(self) -> dict[str, str | int]:
        return asdict(self)


def parse_wikisource(html: str) -> tuple[str, list[str], list[ParsedParagraph]]:
    soup = BeautifulSoup(html, "lxml")
    content = soup.select_one("div.mw-parser-output") or soup
    anchors: list[str] = []
    for h in content.select("span.mw-headline[id]"):
        anchors.append(h.get("id"))
    text_parts = []
    paragraphs: list[ParsedParagraph] = []
    section = "正文"
    idx = 0
    for node in content.select("h1,h2,h3,h4,p,li,dd,dt"):
        if node.name in {"h1", "h2", "h3", "h4"}:
            section = node.get_text(" ", strip=True) or section
            continue
        txt = node.get_text(" ", strip=True)
        if txt:
            paragraphs.append(ParsedParagraph(section_path=section, paragraph_index=idx, text=txt))
            idx += 1

    for node in content.select("p,li,dd,dt"):
        txt = node.get_text(" ", strip=True)
        if txt:
            text_parts.append(txt)
    text = "\n".join(text_parts) if text_parts else content.get_text("\n", strip=True)
    return text, anchors[:200], paragraphs
