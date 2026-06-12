"""Render a shareable verdict card as PNG (Open Graph preview image).
Pure presentation of already-public verdict text — never includes raw intake."""

import io
import re
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont


def plain_text(s: str) -> str:
    """Strip light markdown (bold/italic/heading markers) for image + meta rendering."""
    s = re.sub(r"\*\*|__|^#+\s*", "", s or "", flags=re.MULTILINE)
    s = s.replace("*", "").replace("`", "")
    return re.sub(r"\s+", " ", s).strip()

W, H = 1200, 630
BG = (20, 17, 14)
PANEL = (31, 26, 21)
GOLD = (201, 162, 75)
INK = (236, 227, 212)
MUTED = (168, 155, 134)

_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
_SERIF_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"


@lru_cache
def _font(bold: bool, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(_SERIF_BOLD if bold else _SERIF, size)
    except OSError:
        return ImageFont.load_default()


def _wrap(draw, text, font, max_w, max_lines):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = w
            if len(lines) == max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if len(lines) == max_lines and (len(words) > len(" ".join(lines).split())):
        lines[-1] = lines[-1].rstrip(".,;: ") + "…"
    return lines


def render_card(decision: str, recommendation: str) -> bytes:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # border + panel
    d.rounded_rectangle([24, 24, W - 24, H - 24], radius=20, outline=GOLD, width=2)

    d.text((64, 60), "THE VERDICT", font=_font(True, 34), fill=GOLD)

    y = 150
    d.text((64, y), "On the question of", font=_font(False, 26), fill=MUTED)
    y += 44
    for line in _wrap(d, plain_text(decision) or "a hard decision", _font(True, 52), W - 128, 2):
        d.text((64, y), line, font=_font(True, 52), fill=INK)
        y += 64

    y += 26
    d.line([64, y, W - 64, y], fill=(58, 48, 38), width=1)
    y += 30
    for line in _wrap(d, plain_text(recommendation), _font(False, 36), W - 128, 4):
        d.text((64, y), line, font=_font(False, 36), fill=INK)
        y += 50

    d.text((64, H - 70), "Put your decision on trial · decision-court.jaycurtis.org",
           font=_font(False, 24), fill=MUTED)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
