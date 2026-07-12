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
# The push (last column) must keep the map monotonic, or columns would fold over each other and the skyline
# would smear. That needs  A * pi / (halfW - R) < 1  ->  A < ~183px landscape, ~104px portrait. Well clear.
JOBS = [
    ('assets/menu_bg_land_back2.png',     'assets/menu_bg_land_arcade.png',     0.500, 0.297, 140),
    ('assets/menu_bg_portrait_back2.png', 'assets/menu_bg_portrait_arcade.png', 0.500, 0.084, 86),
]


def build(src_path, dst_path, cx_frac, d_frac, amount):
    im = Image.open(src_path).convert('RGBA')
    W, H = im.size
    src = im.load()
    out = Image.new('RGBA', (W, H))
    dst = out.load()

    cx = cx_frac * W
    R = d_frac * H / 2.0          # sun radius: inside this, nothing moves
    halfW = max(cx, W - cx)

    # Build dest->src for one column at a time. The forward map is monotonic (A * pi / (halfW - R) < 1),
    # so a simple scan inversion is exact enough at 1px resolution.
    from math import sin, pi
    fwd = []
    for x in range(W):
        d = abs(x - cx)
        if d <= R or halfW <= R:
            push = 0.0
        else:
            push = amount * sin(pi * (d - R) / (halfW - R))
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
    print(f'{dst_path}: {W}x{H}  sun R={R:.0f}px untouched, max push {peak:.0f}px')


if __name__ == '__main__':
    for s, d, cx, df, amt in JOBS:
        build(s, d, cx, df, amt)
