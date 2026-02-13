from bs4 import BeautifulSoup


def parse_ctext(html: str) -> tuple[str, list[str]]:
    soup = BeautifulSoup(html, "lxml")
    anchors: list[str] = []
    for tag in soup.select("a[href]"):
        href = tag.get("href", "")
        if "#" in href:
            anchors.append(href)
    text = "\n".join(p.get_text(" ", strip=True) for p in soup.select("p") if p.get_text(strip=True))
    if not text:
        text = soup.get_text("\n", strip=True)
    return text, anchors[:100]
