#!/usr/bin/env python3
"""Build assets/menu_bg_*_arcade.png — the arcade backdrop, with the skyline pushed out to the sides.

In arcade the buildings come from the backdrop IMAGE (the canvas only draws palms there), so they cannot be
moved in code — the art has to move. This applies a horizontal DISPLACEMENT field:

    dest_x = src_x + A * sin(pi * (d - R) / (halfW - R)) * sign(x - cx)      for d > R
    dest_x = src_x                                                            for d <= R   (the sun)

i.e. columns are pushed AWAY from the centre, by nothing at the sun's edge, rising to A px in the middle
distance, and back to nothing at the frame edge. That matters:

  * zero at the sun  -> the sun disc is not stretched into an ellipse (a plain scaleX would have)
  * zero at the edge -> no outer buildings are shoved off-frame and lost, and no empty gutter appears
  * the peak sits exactly where the buildings crowding the sun are, which is what we want moved

Only the ARCADE backdrop gets this. The menu still uses the untouched art: the displacement bends vertical
lines, and the menu shows the image's perspective grid floor, which would visibly warp. In arcade the canvas
paints its own opaque floor over everything below the horizon, so the warp there is never seen.

Usage:  python3 tools/make_arcade_bg.py      (from the project root; needs Pillow)
"""

from PIL import Image

# sun geometry, same numbers the visualiser uses (see SUN in index.html)
# The push is given as a FRACTION OF EACH IMAGE'S OWN CEILING, never as a raw pixel count.
# That matters: portrait is half as wide as landscape (halfW 384 vs 688), so its ceiling is roughly half.
# A pixel amount that is comfortable in landscape is near-fatal in portrait — a shared "170px" put portrait
# at 96% of its limit, squeezing columns 27x, which flattened the sun's sides and smeared the skyline into
# the horizon. The fraction below is the worst-case COMPRESSION: 0.75 means columns never get squeezed more
# than 4x, and only at the very frame edge.
JOBS = [
    ('assets/menu_bg_land_back2.png',     'assets/menu_bg_land_arcade.png',     0.500, 0.297, 0.75),
    ('assets/menu_bg_portrait_back2.png', 'assets/menu_bg_portrait_arcade.png', 0.500, 0.084, 0.55),
]


def build(src_path, dst_path, cx_frac, d_frac, squeeze):
    from math import sin, pi

    im = Image.open(src_path).convert('RGBA')
    W, H = im.size
    src = im.load()
    out = Image.new('RGBA', (W, H))
    dst = out.load()

    cx = cx_frac * W
    R = d_frac * H / 2.0
    R0 = R * 1.30                 # start the ramp CLEAR of the sun, not right on its rim
    halfW = max(cx, W - cx)
    L = halfW - R0

    # Window: sin^2, not sin. sin() has its steepest slope at both ENDS of the ramp, so the old map pinched
    # exactly at the sun's rim and at the frame edge — which is what flattened the sun into a squared-off
    # disc. sin^2 has ZERO slope at both ends, so the warp eases in and out and neither the sun nor the edge
    # is compressed.
    #   amount is derived from the ceiling: max|w'| = pi/L, so a push of A gives a worst-case column
    #   spacing of 1 - A*pi/L. Solving for a chosen squeeze gives A directly, and it can never fold over.
    amount = squeeze * L / pi

    fwd = []
    for x in range(W):
        d = abs(x - cx)
        if d <= R0 or L <= 0:
            push = 0.0
        else:
            u = (d - R0) / L
            push = amount * (sin(pi * u) ** 2)
        sign = 1.0 if x >= cx else -1.0
        fwd.append(x + push * sign)

    # invert: for each destination column, find the source column that lands on it
    inv = [0.0] * W
    j = 0
    for xd in range(W):
        while j < W - 2 and fwd[j + 1] < xd:
            j += 1
        x0, x1 = fwd[j], fwd[j + 1] if j + 1 < W else fwd[j] + 1
        t = 0.0 if x1 == x0 else (xd - x0) / (x1 - x0)
        inv[xd] = max(0.0, min(W - 1.0, j + t))

    for xd in range(W):
        xs = inv[xd]
        x0 = int(xs)
        x1 = min(W - 1, x0 + 1)
        f = xs - x0
        for y in range(H):
            a = src[x0, y]
            b = src[x1, y]
            dst[xd, y] = (
                int(a[0] + (b[0] - a[0]) * f),
                int(a[1] + (b[1] - a[1]) * f),
                int(a[2] + (b[2] - a[2]) * f),
                int(a[3] + (b[3] - a[3]) * f),
            )
    out.save(dst_path)
    peak = max(abs(fwd[x] - x) for x in range(W))
    slope = min(fwd[i] - fwd[i - 1] for i in range(1, W))
    folded = sum(1 for i in range(1, W) if fwd[i] < fwd[i - 1])
    print(f'{dst_path}: {W}x{H} | sun R={R:.0f}px untouched (ramp starts {R0:.0f}px) | '
          f'max push {peak:.0f}px | min column spacing {slope:.2f}px ({1/max(slope,1e-6):.1f}x squeeze) | folded={folded}')
    assert folded == 0, 'columns folded over — the skyline would smear'
    assert slope > 0.2, 'columns squeezed too hard — visible smear at the frame edge'


if __name__ == '__main__':
    for s, d, cx, df, sq in JOBS:
        build(s, d, cx, df, sq)
