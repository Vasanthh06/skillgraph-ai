"""Regenerate the web logo assets from design/logo-source.png (the supplied logo, transparent background).

The supplied wordmark and tagline are dark navy, so they vanish on the app's navy background. For the dark theme we
recolour ONLY those dark-navy pixels to a light tint (leaving the colourful emblem and the green->purple "AI" untouched)
and lighten the mortarboard. Outputs go to frontend/public/.   python design/make_logo_variants.py
"""
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "frontend" / "public"
src = Image.open(HERE / "logo-source.png").convert("RGBA")
A = np.array(src).copy()
H, W = A.shape[:2]
lum = 0.299 * A[..., 0] + 0.587 * A[..., 1] + 0.114 * A[..., 2]
dark = (lum < 95) & (A[..., 3] > 0)
D = A.copy()
text = np.zeros((H, W), bool)
text[770:962, :950] = True      # "SkillGraph" only; stops before the "AI" gradient so it is not touched
text[962:, :] = True            # tagline
D[dark & text, 0:3] = (232, 238, 255)
board = np.zeros((H, W), bool)
board[90:260, 470:780] = True   # mortarboard
D[dark & board, 0:3] = (84, 108, 214)
full = Image.fromarray(D)

em = full.crop((0, 90, W, 745))
em = em.crop(em.split()[3].getbbox())
side = max(em.size)
sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
sq.paste(em, ((side - em.size[0]) // 2, (side - em.size[1]) // 2))

OUT.mkdir(parents=True, exist_ok=True)
sq.resize((256, 256), Image.LANCZOS).save(OUT / "logo-mark.png", optimize=True)
sq.resize((64, 64), Image.LANCZOS).save(OUT / "favicon-64.png", optimize=True)
sq.resize((180, 180), Image.LANCZOS).save(OUT / "apple-touch-icon.png", optimize=True)
full.resize((640, 640), Image.LANCZOS).save(OUT / "logo-full-dark.png", optimize=True)
src.resize((640, 640), Image.LANCZOS).save(OUT / "logo-full-light.png", optimize=True)   # original colours, for light backgrounds
print("wrote logo assets to", OUT)
