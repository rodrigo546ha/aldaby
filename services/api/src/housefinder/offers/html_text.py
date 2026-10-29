"""Texto visible de una página HTML, sin dependencias (ADR-0015).

Se queda con lo que una persona lee: sin scripts, estilos ni plantillas, un bloque por línea. Del
`<head>` solo se toman el título y las imágenes que la página declara para compartir (`og:image`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser

HIDDEN = {"script", "style", "noscript", "template", "svg", "iframe", "head", "object", "canvas"}
BLOCKS = {
    "p", "div", "section", "article", "header", "footer", "main", "aside", "nav", "li", "ul",
    "ol", "table", "tr", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6", "br", "dd", "dt", "dl",
    "figcaption", "blockquote", "pre", "form", "label", "button",
}
VOID = {"br", "img", "meta", "link", "input", "hr", "source", "wbr", "area", "base", "col"}
MAX_IMAGES = 20


@dataclass
class PageText:
    title: str | None = None
    text: str = ""
    images: list[str] = field(default_factory=list)


class _Collector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hidden = 0
        self.in_title = False
        self.title: list[str] = []
        self.lines: list[str] = []
        self.current: list[str] = []
        self.images: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "meta":
            values = dict(attrs)
            if (values.get("property") or values.get("name")) == "og:image" and values.get(
                    "content") and len(self.images) < MAX_IMAGES:
                self.images.append(values["content"] or "")
            return
        if tag == "title":
            self.in_title = True
        if tag in HIDDEN and tag not in VOID:
            self.hidden += 1
        if tag in BLOCKS:
            self._flush()

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False
        if tag in HIDDEN and tag not in VOID and self.hidden:
            self.hidden -= 1
        if tag in BLOCKS:
            self._flush()

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title.append(data)
        elif not self.hidden:
            self.current.append(data)

    def _flush(self) -> None:
        line = " ".join("".join(self.current).split())
        if line:
            self.lines.append(line)
        self.current = []


def page_text(html: str) -> PageText:
    collector = _Collector()
    collector.feed(html)
    collector.close()
    collector._flush()
    title = " ".join("".join(collector.title).split()) or None
    lines: list[str] = []
    for line in collector.lines:
        if not lines or lines[-1] != line:  # menús y botones repetidos seguidos
            lines.append(line)
    return PageText(title=title, text="\n".join(lines), images=collector.images)
