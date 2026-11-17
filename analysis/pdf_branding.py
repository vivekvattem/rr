"""Local RR branding shared by PDF builds; no network access required."""
from pathlib import Path

from reportlab.lib.utils import ImageReader

LOGO = Path(__file__).resolve().parents[1] / 'data/reference/rr_logo.png'
WATERMARK_OPACITY = 0.055


def draw_watermark(canvas, page_width, page_height):
    """Paint a faint logo at the physical page centre, behind all flowables."""
    logo = ImageReader(str(LOGO))
    source_width, source_height = logo.getSize()
    height = min(330, page_height * 0.42)
    width = height * source_width / source_height
    canvas.saveState()
    canvas.setFillAlpha(WATERMARK_OPACITY)
    canvas.drawImage(logo, (page_width - width) / 2,
                     (page_height - height) / 2,
                     width=width, height=height, mask='auto')
    canvas.restoreState()
