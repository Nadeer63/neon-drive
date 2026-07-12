#!/usr/bin/env python3
"""Build assets/palm_neon.png — the ARCADE palm, with the baked-in opaque fill removed.

The hand-made palm art (palm_solid / palm_grounded / palm_sprite / palm_lush) is neon strokes drawn
ON TOP OF an opaque dark shape: a rectangular block under the crown and a wide slab behind the trunk.
On a dark background that fill is invisible, so it looks like a clean neon outline. It isn't. The palms
are drawn over the lit sky and the sun, and there the fill shows as a chunky box — and because arcade
recolours the palm with ctx.filter = hue-rotate(...), the fill gets dragged along with the neon
(a pink box from palm_grounded, a black one from palm_solid).

Fix: keep only the neon, throw the fill away, rebuild the halo from the tubes.

  * brightness V = max(R,G,B) is cleanly BIMODAL — the fill sits at V < ~110, the neon at V > ~140,
    with a valley around 120. So a smoothstep across the valley separates them exactly.
  * the original glow lived inside the dark band we just deleted, so blur the surviving tubes to
    regenerate a halo.
  * frond colours are kept as-is; only the halo is flattened to GRID_CYAN, the cyan the arcade grid uses.

Usage:  python3 tools/make_palm_neon.py        (run from the project root; needs Pillow)
"""

from PIL import Image, ImageChops, ImageFilter

SRC = 'assets/palm_solid.png'
DST = 'assets/palm_neon.png'
DST_PINK = 'assets/palm_neon_pink.png'

LO, HI = 100, 150          # the histogram valley: below = opaque fill, above = neon
GLOW_RADIUS = 7            # tight halo; wider blurs the fronds into a white blob
GLOW_STRENGTH = 0.6
GLOW_COL = (65, 237, 241)  # GRID_CYAN — the same cyan the arcade floor grid is drawn in

# ---- the PINK palm, baked ----
# The game used to recolour the cyan palm at draw time with ctx.filter = hue-rotate(138deg)...
# That is a trap on mobile: canvas filters are unsupported on older iOS Safari, where the call silently
# does nothing and the palms come out BLUE — the original cyan art, un-recoloured. Baking the pink into the
# asset removes the runtime dependency completely, so the palm looks identical on every browser (and it is
# faster too — no filter pass, and no offscreen bake at load).
PINK_GLOW = (255, 70, 205)    # GRID_PINK
PINK_CORE = (255, 214, 242)   # hot centre of the neon tube


def smoothstep(v, lo, hi):
    t = max(0.0, min(1.0, (v - lo) / (hi - lo)))
    return t * t * (3 - 2 * t)


def main():
    im = Image.open(SRC).convert('RGBA')
    r, g, b, alpha = im.split()
    v = ImageChops.lighter(ImageChops.lighter(r, g), b)

    core = ImageChops.multiply(v.point(lambda x: int(255 * smoothstep(x, LO, HI))), alpha)
    glow = core.filter(ImageFilter.GaussianBlur(GLOW_RADIUS)).point(lambda x: int(x * GLOW_STRENGTH))

    rgb = Image.composite(im.convert('RGB'), Image.new('RGB', im.size, GLOW_COL), core)
    out = rgb.convert('RGBA')
    out.putalpha(ImageChops.lighter(core, glow))
    out.save(DST)

    # PINK variant: same alpha (same neon shape), colour painted in rather than hue-rotated at runtime.
    # Map each pixel's BRIGHTNESS onto a pink ramp (GRID_PINK -> hot core) instead of flat-filling by a
    # threshold. A flat fill throws away the tube's internal shading and the crown comes out as one pale
    # pink blob with no fronds — the brightness ramp keeps every frond and rung.
    lo2, hi2 = 90, 255
    t = v.point(lambda x: int(255 * max(0.0, min(1.0, (x - lo2) / (hi2 - lo2)))))
    chans = []
    for i in range(3):
        c0, c1 = PINK_GLOW[i], PINK_CORE[i]
        chans.append(t.point(lambda x, c0=c0, c1=c1: int(c0 + (c1 - c0) * x / 255)))
    pk = Image.merge('RGB', chans).convert('RGBA')
    pk.putalpha(ImageChops.lighter(core, glow))
    pk.save(DST_PINK)
    print(f'{DST_PINK}: pink baked in (no runtime ctx.filter needed)')

    px = out.load()
    w, h = out.size
    opaque = dark = 0
    for y in range(0, h, 3):
        for x in range(0, w, 3):
            cr, cg, cb, ca = px[x, y]
            if ca > 200:
                opaque += 1
                if max(cr, cg, cb) < 70:
                    dark += 1
    print(f'{DST}: opaque px={opaque}, opaque-dark fill remaining={dark}')
    if dark:
        raise SystemExit('FAILED: opaque dark fill survived — widen the LO/HI band')


if __name__ == '__main__':
    main()
