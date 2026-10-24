"""Vector-drawn cartoon characters (PIL). Sprites are drawn at 2x and downsampled for anti-aliasing.
Dr. Meera - clinician.  Gluco - the digital twin, a friendly purple droplet with a screen face."""
import math

from PIL import Image, ImageDraw

S = 2           # supersampling
W, H = 220, 340  # final sprite size


def _canvas():
    return Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))


def _p(*v):
    return [int(x * S) for x in v]


def meera(mouth=0, blink=False):
    im = _canvas(); d = ImageDraw.Draw(im)
    skin, skin_d = (190, 128, 92), (160, 102, 72)
    hair = (38, 26, 22)
    coat, coat_s = (250, 251, 252), (214, 221, 228)
    scrub = (14, 124, 134)
    # body / coat
    d.rounded_rectangle(_p(30, 225, 190, 360), radius=40 * S, fill=coat, outline=coat_s, width=2 * S)
    d.polygon(_p(88, 225, 132, 225, 110, 285), fill=scrub)                 # scrub V
    d.line(_p(110, 285, 110, 340), fill=coat_s, width=2 * S)               # coat opening
    d.polygon(_p(70, 228, 88, 225, 104, 290, 92, 300), fill=(236, 240, 244))  # lapels
    d.polygon(_p(150, 228, 132, 225, 116, 290, 128, 300), fill=(236, 240, 244))
    # stethoscope
    d.arc(_p(72, 210, 148, 300), start=20, end=160, fill=(60, 70, 80), width=4 * S)
    d.line(_p(80, 262, 74, 300), fill=(60, 70, 80), width=4 * S)
    d.ellipse(_p(64, 296, 84, 316), fill=(150, 160, 170), outline=(60, 70, 80), width=2 * S)
    # name badge
    d.rounded_rectangle(_p(140, 262, 172, 278), radius=3 * S, fill=(14, 124, 134))
    # neck
    d.rounded_rectangle(_p(96, 190, 124, 232), radius=10 * S, fill=skin_d)
    # hair back
    d.ellipse(_p(46, 52, 174, 200), fill=hair)
    d.ellipse(_p(80, 20, 140, 72), fill=hair)          # bun
    # face
    d.ellipse(_p(58, 68, 162, 196), fill=skin)
    d.ellipse(_p(50, 120, 66, 146), fill=skin_d)       # ears
    d.ellipse(_p(154, 120, 170, 146), fill=skin_d)
    d.ellipse(_p(54, 142, 60, 148), fill=(232, 163, 61))  # earrings
    d.ellipse(_p(160, 142, 166, 148), fill=(232, 163, 61))
    # fringe
    d.chord(_p(56, 60, 164, 140), start=180, end=360, fill=hair)
    d.polygon(_p(60, 100, 92, 78, 70, 128), fill=hair)
    # brows
    d.arc(_p(74, 104, 100, 116), start=200, end=340, fill=hair, width=3 * S)
    d.arc(_p(120, 104, 146, 116), start=200, end=340, fill=hair, width=3 * S)
    # eyes
    for cx in (87, 133):
        if blink:
            d.arc(_p(cx - 9, 118, cx + 9, 132), start=20, end=160, fill=(40, 30, 30), width=3 * S)
        else:
            d.ellipse(_p(cx - 9, 116, cx + 9, 136), fill=(255, 255, 255))
            d.ellipse(_p(cx - 5, 120, cx + 5, 134), fill=(55, 38, 30))
            d.ellipse(_p(cx - 1, 122, cx + 3, 126), fill=(255, 255, 255))
    # nose + cheeks
    d.arc(_p(104, 132, 116, 152), start=300, end=60, fill=skin_d, width=2 * S)
    d.ellipse(_p(70, 146, 88, 158), fill=(204, 128, 100))
    d.ellipse(_p(132, 146, 150, 158), fill=(204, 128, 100))
    _mouth(d, 110, 166, mouth, lip=(150, 60, 60))
    return im.resize((W, H), Image.LANCZOS)


def gluco(mouth=0, blink=False, glow=1.0):
    im = _canvas(); d = ImageDraw.Draw(im)
    purple, purple_d = (122, 90, 248), (95, 66, 214)
    cx, top, bottom = 110, 70, 320
    # antenna
    d.line(_p(cx, top + 6, cx, 34), fill=purple_d, width=4 * S)
    g = int(180 + 75 * glow)
    d.ellipse(_p(cx - 13, 14, cx + 13, 40), fill=(255, g, 120))
    # teardrop body
    pts = []
    for k in range(200):
        t = k / 199 * 2 * math.pi
        x = math.sin(t) * (1 - math.cos(t)) ** 0.9 * 0.5
        y = -math.cos(t)
        pts.append((cx + x * 190, top + (y + 1) / 2 * (bottom - top)))
    d.polygon([(int(a * S), int(b * S)) for a, b in pts], fill=purple)
    # arms
    d.ellipse(_p(14, 214, 50, 250), fill=purple_d)
    d.ellipse(_p(170, 214, 206, 250), fill=purple_d)
    # belly screen with glucose line
    d.rounded_rectangle(_p(64, 252, 156, 300), radius=12 * S, fill=(242, 239, 255))
    line = [(70, 288), (84, 284), (96, 270), (106, 262), (116, 276), (128, 282), (140, 280), (150, 274)]
    d.line([(int(a * S), int(b * S)) for a, b in line], fill=(214, 73, 51), width=3 * S, joint="curve")
    d.line(_p(68, 268, 152, 268), fill=(46, 158, 106), width=1 * S)
    # face screen
    d.rounded_rectangle(_p(48, 150, 172, 238), radius=26 * S, fill=(22, 33, 43))
    for ex in (86, 134):
        if blink:
            d.line(_p(ex - 11, 186, ex + 11, 186), fill=(94, 234, 212), width=4 * S)
        else:
            d.rounded_rectangle(_p(ex - 10, 170, ex + 10, 198), radius=9 * S, fill=(94, 234, 212))
            d.ellipse(_p(ex - 2, 174, ex + 5, 181), fill=(220, 255, 250))
    _mouth(d, 110, 214, mouth, lip=(94, 234, 212), dark=True)
    # cheeks
    d.ellipse(_p(58, 200, 72, 210), fill=(150, 70, 110))
    d.ellipse(_p(148, 200, 162, 210), fill=(150, 70, 110))
    return im.resize((W, H), Image.LANCZOS)


def _mouth(d, cx, cy, state, lip, dark=False):
    if state == 0:
        d.arc(_p(cx - 14, cy - 8, cx + 14, cy + 8), start=20, end=160, fill=lip, width=3 * S)
    elif state == 1:
        d.ellipse(_p(cx - 10, cy - 3, cx + 10, cy + 9), fill=(70, 20, 30) if not dark else (10, 60, 60), outline=lip, width=2 * S)
    else:
        d.ellipse(_p(cx - 12, cy - 6, cx + 12, cy + 16), fill=(70, 20, 30) if not dark else (10, 60, 60), outline=lip, width=2 * S)
        d.ellipse(_p(cx - 6, cy + 6, cx + 6, cy + 14), fill=(220, 110, 120) if not dark else (60, 180, 170))


def sprites():
    out = {}
    for name, fn in (("M", meera), ("G", gluco)):
        for m in (0, 1, 2):
            for b in (False, True):
                out[(name, m, b)] = fn(m, b)
    return out


if __name__ == "__main__":
    sp = sprites()
    sheet = Image.new("RGBA", (W * 6, H * 2), (11, 60, 73, 255))
    for i, m in enumerate((0, 1, 2)):
        for j, b in enumerate((False, True)):
            sheet.alpha_composite(sp[("M", m, b)], (W * (i * 2 + j), 0))
            sheet.alpha_composite(sp[("G", m, b)], (W * (i * 2 + j), H))
    sheet.save("sprite_sheet.png")
