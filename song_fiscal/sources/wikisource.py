from bs4 import BeautifulSoup


def parse_wikisource(html: str) -> tuple[str, list[str]]:
    soup = BeautifulSoup(html, "lxml")
    content = soup.select_one("div.mw-parser-output") or soup
    anchors: list[str] = []
    for h in content.select("span.mw-headline[id]"):
        anchors.append(h.get("id"))
    text_parts = []
    for node in content.select("p,li,dd,dt"):
        txt = node.get_text(" ", strip=True)
        if txt:
            text_parts.append(txt)
    text = "\n".join(text_parts) if text_parts else content.get_text("\n", strip=True)
    return text, anchors[:200]
