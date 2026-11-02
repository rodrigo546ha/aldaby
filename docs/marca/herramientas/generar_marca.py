"""Genera los SVG de la marca Aldaby con el logotipo en trazos.

Uso: services/api/.venv/bin/python -I docs/marca/herramientas/generar_marca.py <fuente.ttf> docs/marca
"""

import sys
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

INK = "#0F3B2E"
BRASS = "#E3A92B"
SAND = "#F6EBD0"
WHITE = "#FFFFFF"
WORD = "aldaby"
TRACKING = -0.045  # em, como en la propuesta

# Símbolo en una rejilla de 64: soporte, cuello, anilla y clavo.
RING = (
    "M32 16a19.5 19.5 0 1 1 0 39a19.5 19.5 0 1 1 0-39Z"
    "M32 23a12.5 12.5 0 1 0 0 25a12.5 12.5 0 1 0 0-25Z"
)
MOUNT = "M32 2a7 7 0 1 1 0 14a7 7 0 1 1 0-14ZM29 13h6v7h-6Z"
STUD = "M32 57a3 3 0 1 1 0 6a3 3 0 1 1 0-6Z"


def symbol(ink: str, ring: str) -> str:
    return (
        f'<path fill="{ink}" d="{MOUNT}{STUD}"/>'
        f'<path fill="{ring}" fill-rule="evenodd" d="{RING}"/>'
    )


def wordmark(font_path: str) -> tuple[str, float, float, float, float]:
    """Devuelve el path del logotipo en unidades de 64 por em y su caja (x0, y0, x1, y1)."""
    font = TTFont(font_path)
    font = instantiateVariableFont(font, {"wght": 800, "opsz": 96, "wdth": 100})
    upm = font["head"].unitsPerEm
    cmap = font.getBestCmap()
    glyphs = font.getGlyphSet()
    hmtx = font["hmtx"]
    scale = 64 / upm
    pen = SVGPathPen(glyphs)
    bounds = BoundsPen(glyphs)
    x = 0.0
    names = [cmap[ord(c)] for c in WORD]
    for i, name in enumerate(names):
        # y hacia abajo en SVG: espejo vertical y escala a la rejilla de 64
        t = (scale, 0, 0, -scale, x, 0)
        glyphs[name].draw(TransformPen(pen, t))
        glyphs[name].draw(TransformPen(bounds, t))
        x += hmtx[name][0] * scale
        if i < len(names) - 1:
            x += TRACKING * 64
    x0, y0, x1, y1 = bounds.bounds
    return pen.getCommands(), x0, y0, x1, y1


def svg(width: float, height: float, body: str, title: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:g} {height:g}" '
        f'role="img" aria-label="{title}"><title>{title}</title>{body}</svg>\n'
    )


def main() -> None:
    font_path, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    word, x0, y0, x1, y1 = wordmark(font_path)

    # El símbolo ocupa del alto de la "l" al fondo de la "y". La anilla va de x=12,5 a x=51,5
    # en su rejilla: el logo empieza en su borde y el texto queda a 0,16 em de ella.
    size = y1 - y0
    k = size / 64
    gap = 0.16 * 64
    wx = 39 * k + gap - x0
    total_w = wx + x1

    def lockup(ink: str, ring: str, text: str) -> str:
        return (
            f'<g transform="translate({-12.5 * k:.3f} 0) scale({k:.5f})">{symbol(ink, ring)}</g>'
            f'<path fill="{text}" transform="translate({wx:.3f} {-y0:.3f})" d="{word}"/>'
        )

    files = {
        "aldaby-simbolo.svg": svg(64, 64, symbol(INK, BRASS), "Aldaby"),
        "aldaby-simbolo-negativo.svg": svg(64, 64, symbol(WHITE, BRASS), "Aldaby"),
        "aldaby-logo.svg": svg(total_w, size, lockup(INK, BRASS, INK), "Aldaby"),
        "aldaby-logo-negativo.svg": svg(total_w, size, lockup(WHITE, BRASS, WHITE), "Aldaby"),
        "aldaby-logotipo.svg": svg(
            x1 - x0, size,
            f'<path fill="{INK}" transform="translate({-x0:.3f} {-y0:.3f})" d="{word}"/>',
            "Aldaby",
        ),
        "aldaby-icono-app.svg": svg(
            64, 64,
            f'<rect width="64" height="64" rx="14" fill="{INK}"/>'
            f'<g transform="translate(11.5 11.5) scale(0.64)">{symbol(WHITE, BRASS)}</g>',
            "Aldaby",
        ),
        "favicon.svg": svg(
            64, 64,
            "<style>.i{fill:" + INK + "}@media (prefers-color-scheme:dark){.i{fill:" + WHITE + "}}</style>"
            f'<path class="i" d="{MOUNT}{STUD}"/>'
            f'<path fill="{BRASS}" fill-rule="evenodd" d="{RING}"/>',
            "Aldaby",
        ),
    }
    for name, content in files.items():
        (out / name).write_text(content, encoding="utf-8")
        print(name, len(content))


if __name__ == "__main__":
    main()
