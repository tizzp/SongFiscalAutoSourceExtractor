from dataclasses import asdict, dataclass

from bs4 import BeautifulSoup


@dataclass
class ParsedParagraph:
    section_path: str
    paragraph_index: int
    text: str

    def to_dict(self) -> dict[str, str | int]:
        return asdict(self)


def parse_ctext(html: str) -> tuple[str, list[str], list[ParsedParagraph]]:
    soup = BeautifulSoup(html, "lxml")
    anchors: list[str] = []
    for tag in soup.select("a[href]"):
        href = tag.get("href", "")
        if "#" in href:
            anchors.append(href)
    paragraphs: list[ParsedParagraph] = []
    section = "正文"
    idx = 0
    for node in soup.select("h1,h2,h3,h4,p,li,dd,dt"):
        if node.name in {"h1", "h2", "h3", "h4"}:
            section = node.get_text(" ", strip=True) or section
            continue
        txt = node.get_text(" ", strip=True)
        if txt:
            paragraphs.append(ParsedParagraph(section_path=section, paragraph_index=idx, text=txt))
            idx += 1
    text = "\n".join(p.text for p in paragraphs) if paragraphs else soup.get_text("\n", strip=True)
    return text, anchors[:100], paragraphs
