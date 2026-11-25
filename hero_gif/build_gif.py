"""
Hero GIF (CPU only): compose assets/hero.gif from panels of the paper's own figures.

Five scenes: the observation (paper Fig. 1a), the instance emergence point (Fig. 1b, Eq. 1, Fig. 8), the edge
(ABDiv and one-step self-distillation: Fig. 4, Eq. 2, Fig. 5), the masks (Fig. 2, Fig. 9a) and the results
(Fig. 10, Tables 1, 2, 5, 6). Every image is a panel of a figure of the ICLR 2026 paper, stored in panels/;
every label and number is in scenes.json and comes from the paper. No model is needed.

    python hero_gif/build_gif.py                  # writes assets/hero.gif
    python hero_gif/build_gif.py --preview DIR    # writes every frame to DIR as a PNG instead

The committed GIF was rendered on Windows with Segoe UI. On other systems the script falls back to the
DejaVu Sans bundled with matplotlib (set a little smaller, because it is wider): same layout, different glyphs.
"""
import argparse
import json
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

ap = argparse.ArgumentParser()
ap.add_argument('--out', default=os.path.join(ROOT, 'assets', 'hero.gif'))
ap.add_argument('--preview', metavar='DIR', help='write the frames as PNGs to DIR and skip the GIF')
args = ap.parse_args()

W, H = 1280, 960
TEAL, TEAL_BG, MINT_LINE = (0, 102, 102), (232, 245, 244), (150, 205, 200)
INK, MUTED, LINE, WHITE, GREY = (16, 24, 31), (91, 105, 117), (220, 229, 233), (255, 255, 255), (178, 188, 196)
TAB_DIM = (191, 217, 217)                                          # inactive scene tab
BASE = (0, 110, 175)                                               # baselines and semantic states
SOFT = (215, 238, 236)                                             # small text on a teal card
COL = {'ours': TEAL, 'base': BASE, 'muted': MUTED}
M, TOP, NOTE_Y = 24, 214, 938                                      # side margin · top of the panels · baseline note
V = json.load(open(os.path.join(HERE, 'scenes.json'), encoding='utf-8'))

WIN_FONTS = 'C:/Windows/Fonts'
FALLBACK = {'segoeui.ttf': 'DejaVuSans.ttf', 'seguisb.ttf': 'DejaVuSans-Bold.ttf', 'segoeuib.ttf': 'DejaVuSans-Bold.ttf'}


def F(name, size):
    path = os.path.join(WIN_FONTS, name)
    if not os.path.exists(path):                                   # DejaVu Sans is wider than Segoe UI, so it is set a little smaller
        import matplotlib
        path, size = os.path.join(matplotlib.get_data_path(), 'fonts', 'ttf', FALLBACK[name]), round(size * 0.85)
    return ImageFont.truetype(path, size)


F_TITLE, F_BADGE, F_AWARD, F_SUBT, F_TAB = F('segoeuib.ttf', 40), F('seguisb.ttf', 16), F('segoeuib.ttf', 16), F('segoeui.ttf', 17), F('segoeuib.ttf', 16)
F_HEAD, F_H, F_HS, F_HSUB = F('segoeuib.ttf', 22), F('segoeuib.ttf', 20), F('segoeui.ttf', 16), F('segoeui.ttf', 12)
F_HB, F_HBSUB = F('segoeuib.ttf', 17), F('segoeuib.ttf', 12)
F_MSG, F_NOTE, F_TICK = F('segoeuib.ttf', 20), F('segoeui.ttf', 15), F('segoeui.ttf', 14)
F_NUM, F_BIG, F_FORM, F_FSUB = F('segoeuib.ttf', 26), F('segoeuib.ttf', 34), F('segoeui.ttf', 18), F('segoeui.ttf', 13)


def logo(name, height):
    im = Image.open(os.path.join(HERE, 'logos', name)).convert('RGBA')
    return im.resize((round(im.width * height / im.height), height), Image.LANCZOS)


LOGO_L, LOGO_R = logo('ogq.png', 40), logo('snu.png', 54)          # affiliations in the order of the paper: OGQ, Seoul National University


def load(name, size):
    return Image.open(os.path.join(HERE, 'panels', name)).convert('RGB').resize(size, Image.LANCZOS)


def rrect(dr, box, r, fill=None, outline=None, width=1):
    dr.rounded_rectangle(box, r, fill=fill, outline=outline, width=width)


def rich(dr, x, y, s, font, sub, fill, anchor='l'):
    """Text with subscripts _{...} (one more level inside is smaller) and superscripts ^{...}; y is the baseline. Returns the width."""
    runs, stack, buf, i = [], [0], '', 0
    while i < len(s):
        if s.startswith(('_{', '^{'), i):
            runs.append((buf, stack[-1])); buf = ''
            stack.append(-1 if s[i] == '^' else min(stack[-1] + 1, 2)); i += 2
        elif s[i] == '}' and len(stack) > 1:
            runs.append((buf, stack.pop())); buf = ''; i += 1
        else:
            buf += s[i]; i += 1
    runs.append((buf, stack[-1]))
    fonts = {0: font, 1: sub, 2: sub.font_variant(size=max(9, round(sub.size * 0.82))), -1: sub}
    dy = {0: 0, 1: round(sub.size * 0.3), 2: round(sub.size * 0.55), -1: -round(font.size * 0.38)}
    widths = [dr.textlength(t, font=fonts[l]) for t, l in runs]
    x -= {'l': 0, 'm': sum(widths) / 2, 'r': sum(widths)}[anchor]
    for (t, l), w in zip(runs, widths):
        dr.text((x, y + dy[l]), t, font=fonts[l], fill=fill, anchor='ls')
        x += w
    return sum(widths)


def plain(s):
    return s.replace('_{', '').replace('^{', '').replace('}', '')


def wrap(dr, text, font, width):
    lines, cur = [], ''
    for word in text.split():
        t = (cur + ' ' + word).strip()
        if cur and dr.textlength(t, font=font) > width:
            lines.append(cur); cur = word
        else:
            cur = t
    return lines + [cur]


def fits(dr, text, font, width):
    """The build stops if a label is wider than its column."""
    assert dr.textlength(plain(text), font=font) <= width, (text, dr.textlength(plain(text), font=font), width)
    return text


def line(dr, y, text, font, fill, sub=F_HBSUB):
    """One centered line; the build stops if it does not fit between the side margins."""
    fits(dr, text, font, W - 2 * M)
    rich(dr, W / 2, y + font.size * 0.36, text, font, sub, fill, anchor='m')


def canvas(scene, head, note):
    """White frame with the header: logos, title and venue, subtitle, scene tabs, the scene headline and its note."""
    im = Image.new('RGB', (W, H), WHITE); dr = ImageDraw.Draw(im)
    im.paste(LOGO_L, (34, 22), LOGO_L)
    im.paste(LOGO_R, (W - 34 - LOGO_R.width, 14), LOGO_R)
    venue, award = V['badge']
    tw, vw, aw = dr.textlength(V['title'], font=F_TITLE), dr.textlength(venue, font=F_BADGE), dr.textlength(award, font=F_AWARD)
    bw = 14 + vw + 19 + aw + 14
    x0 = (W - (tw + 14 + bw)) / 2; bx = x0 + tw + 14
    dr.text((x0, 6), V['title'], font=F_TITLE, fill=TEAL)
    rrect(dr, (bx, 22, bx + bw, 50), 14, fill=TEAL)
    dr.text((bx + 14, 36), venue, font=F_BADGE, fill=WHITE, anchor='lm')
    dr.line((bx + 14 + vw + 9, 28, bx + 14 + vw + 9, 44), fill=MINT_LINE, width=1)
    dr.text((bx + 14 + vw + 19, 36), award, font=F_AWARD, fill=WHITE, anchor='lm')
    line(dr, 74, V['subtitle'], F_SUBT, MUTED)
    tabs = V['tabs']                                               # fixed position and size, only the current one is solid
    tw_ = (W - 2 * M - 16 * (len(tabs) - 1)) / len(tabs); x = M
    for i, t in enumerate(tabs):
        rrect(dr, (x, 96, x + tw_, 122), 8, fill=TEAL if i == scene else TAB_DIM)
        dr.text((x + tw_ / 2, 109), t, font=F_TAB, fill=WHITE if i == scene else TEAL, anchor='mm')
        x += tw_ + 16
    line(dr, 154, head, F_HEAD, INK)
    line(dr, NOTE_Y, note, F_NOTE, MUTED)
    return im, dr


def framed(im, dr, pic, x, y, col=GREY, width=2):
    """A picture with a frame drawn around it (outside, so a thick frame does not cover the picture)."""
    im.paste(pic, (x, y))
    dr.rectangle((x - width, y - width, x + pic.width - 1 + width, y + pic.height - 1 + width), outline=col, width=width)


def placeholder(dr, x, y, w, h, label=''):
    rrect(dr, (x, y, x + w - 1, y + h - 1), 10, fill=TEAL_BG, outline=MINT_LINE)
    dr.text((x + w / 2, y + h / 2), label, font=F_H, fill=MINT_LINE, anchor='mm')


def badge(dr, cx, cy, sym, col):
    dr.ellipse((cx - 19, cy - 19, cx + 19, cy + 19), fill=WHITE, outline=col, width=3)
    dr.text((cx, cy - 1), sym, font=F_HEAD, fill=col, anchor='mm')


def timeline(dr, y, xs, done, label):
    """A process arrow under a row of panels: one dot per panel, solid for the steps shown so far."""
    dr.line((xs[0], y, xs[-1] + 44, y), fill=GREY, width=3)
    dr.polygon([(xs[-1] + 58, y), (xs[-1] + 44, y - 7), (xs[-1] + 44, y + 7)], fill=GREY)
    for k, x in enumerate(xs):
        dr.ellipse((x - 7, y - 7, x + 7, y + 7), fill=TEAL if k < done else WHITE, outline=TEAL if k < done else GREY, width=2)
    dr.text((W / 2, y + 22), label, font=F_HS, fill=MUTED, anchor='mm')


def paragraph(dr, x, y, text, font, fill, width, step):
    for t in wrap(dr, text, font, width):
        dr.text((x, y), fits(dr, t, font, width), font=font, fill=fill, anchor='ls'); y += step
    return y


# ---------------------------------------------------------------- scene 1: the observation (paper Fig. 1a)
O = V['observation']
P1 = 236; G1 = (W - 2 * M - 5 * P1) / 4
X1 = [round(M + k * (P1 + G1)) for k in range(5)]
Y1 = [TOP, TOP + P1 + 40]
OBS = {(r, t): load(pat % t, (P1, P1)) for r, (_, pat) in enumerate(O['rows']) for t in O['steps']}
OBS_IMG = load(O['image'], (P1, P1))


def observation_frame(s):
    im, dr = canvas(0, O['head'], O['note'])
    n = len(O['steps'])
    for r, (label, _) in enumerate(O['rows']):
        dr.text((M, Y1[r] - 10), label, font=F_H, fill=TEAL if r == 0 else BASE, anchor='ls')
        for k, t in enumerate(O['steps']):
            if k > s:
                placeholder(dr, X1[k], Y1[r], P1, P1, 'τ = %d' % int(t))
            elif r == 0 and t == O['highlight']:
                framed(im, dr, OBS[r, t], X1[k], Y1[r], TEAL, 4)
            else:
                framed(im, dr, OBS[r, t], X1[k], Y1[r])
    dr.text((X1[4], Y1[0] - 10), 'Generated image', font=F_H, fill=MUTED if s >= n - 1 else GREY, anchor='ls')
    if s >= n - 1:
        framed(im, dr, OBS_IMG, X1[4], Y1[0])
    else:
        placeholder(dr, X1[4], Y1[0], P1, P1, 'τ = 0')
    if s >= n:                                                     # the takeaway, next to the cross-attention row
        title, *body = O['card']
        rrect(dr, (X1[4], Y1[1], X1[4] + P1 - 1, Y1[1] + P1 - 1), 12, fill=TEAL)
        dr.text((X1[4] + 18, Y1[1] + 40), title, font=F_H, fill=WHITE, anchor='ls')
        y = Y1[1] + 76
        for b in body:
            y = paragraph(dr, X1[4] + 18, y, b, F_HS, WHITE, P1 - 36, 23) + 12
        assert y <= Y1[1] + P1, y
    timeline(dr, Y1[1] + P1 + 26, [x + P1 // 2 for x in X1], min(s + 1, n) + (s >= n - 1), O['timeline'])
    line(dr, 830, O['messages'][s], F_MSG, TEAL if s in (1, n) else INK)
    return im


# ---------------------------------------------------------------- scene 2: the instance emergence point (paper Fig. 1b, Eq. 1, Fig. 8)
E = V['emergence']
EM_IMG = load(E['image'], (P1, P1))
EM_SA = [load(p, (P1, P1)) for p, _, _ in E['steps']]
BH = round(P1 * 86.4 / 108.0)
EM_B = [load(p, (P1, BH)) for p, _ in E['backbones']]
YB2 = TOP + P1 + 178                                               # top of the backbone row


def emergence_frame(s):
    im, dr = canvas(1, E['head'], E['note'])
    n = len(E['steps'])
    dr.text((X1[0], TOP - 10), 'Real image', font=F_H, fill=MUTED, anchor='ls')
    framed(im, dr, EM_IMG, X1[0], TOP)
    for k, (_, state, col) in enumerate(E['steps']):
        x = X1[k + 1]
        if k > s:
            placeholder(dr, x, TOP, P1, P1)
            continue
        dr.text((x, TOP - 10), state, font=F_H, fill=COL[col], anchor='ls')
        framed(im, dr, EM_SA[k], x, TOP, *((TEAL, 4) if col == 'ours' else (GREY, 2)))
    timeline(dr, TOP + P1 + 24, [x + P1 // 2 for x in X1], min(s + 2, n + 1), E['timeline'])
    y = TOP + P1 + 62                                              # the criterion
    rrect(dr, (M, y, W - M, y + 70), 12, fill=TEAL_BG, outline=MINT_LINE)
    fits(dr, E['formula_text'], F_HS, 760)
    dr.text((M + 20, y + 35), E['formula_text'], font=F_HS, fill=INK, anchor='lm')
    fits(dr, E['formula'], F_FORM, 400)
    rich(dr, W - M - 20, y + 41, E['formula'], F('segoeuib.ttf', 18), F_FSUB, TEAL, anchor='r')
    dr.text((M, YB2 - 10), E['backbones_title'], font=F_H, fill=INK if s >= n else GREY, anchor='ls')
    for k, (_, label) in enumerate(E['backbones']):
        if s >= n:
            framed(im, dr, EM_B[k], X1[k], YB2)
            dr.text((X1[k] + P1 / 2, YB2 + BH + 18), fits(dr, label, F_HS, P1), font=F_HS, fill=INK, anchor='mm')
        else:
            placeholder(dr, X1[k], YB2, P1, BH, label if k else '')
    line(dr, 884, E['messages'][s], F_MSG, TEAL if s in (2, n) else INK)
    return im


# ---------------------------------------------------------------- scene 3: the edge (paper Fig. 4, Eq. 2, Fig. 5)
D = V['edge']
C3, G3 = 296, 16
X3 = [M + k * (C3 + G3) for k in range(4)]
EH = round(C3 * 0.868)                                             # the edge panels of Fig. 4 without their label banner
YA, YB3 = TOP, TOP + C3 + 44
ED_IMG, ED_SA, ED_E = load(D['image'], (C3, C3)), load(D['sa'], (C3, C3)), load(D['pseudo'], (C3, EH))
ED_T = [load(p, (C3, EH)) for p, _ in D['training']]


def edge_frame(s):
    im, dr = canvas(2, D['head'], D['note'])
    dr.text((X3[0], YA - 10), 'Input image', font=F_HB, fill=MUTED, anchor='ls')
    framed(im, dr, ED_IMG, X3[0], YA)
    rich(dr, X3[1], YA - 10, 'SA(X_{t*}) at the emergence point', F_HB, F_HBSUB, TEAL)
    framed(im, dr, ED_SA, X3[1], YA, TEAL, 3)
    rich(dr, X3[2], YA - 10, 'Pseudo edge map E (ABDiv)', F_HB, F_HBSUB, TEAL if s >= 1 else GREY)
    box = (X3[3], YA, X3[3] + C3 - 1, YA + C3 - 1)
    if s >= 1:
        framed(im, dr, ED_E, X3[2], YA, TEAL, 3)
        A = D['abdiv']
        rrect(dr, box, 12, fill=TEAL_BG, outline=MINT_LINE)
        x, y = box[0] + 18, box[1] + 36
        dr.text((x, y), fits(dr, A['title'], F_HB, C3 - 36), font=F_HB, fill=TEAL, anchor='ls'); y += 36
        for f in A['formula']:
            fits(dr, f, F_FORM, C3 - 30)
            rich(dr, x, y, f, F_FORM, F_FSUB, INK); y += 29
        y = paragraph(dr, x, y + 6, A['text'], F_HS, MUTED, C3 - 36, 22) + 12
        for name, value in A['values']:
            dr.text((x, y), name, font=F_HB, fill=INK, anchor='ls')
            dr.text((box[2] - 18, y), value, font=F_NUM, fill=TEAL if name.startswith('Boundary') else BASE, anchor='rs'); y += 31
        dr.text((x, y - 8), A['source'], font=F_TICK, fill=MUTED, anchor='ls')
        assert y <= box[3], y
    else:
        placeholder(dr, X3[2], YA, C3, EH, 'E')
        placeholder(dr, *box[:2], C3, C3, 'ABDiv')
    badge(dr, X3[1] - G3 / 2, YA + C3 / 2, '→', TEAL)
    if s >= 1:
        badge(dr, X3[2] - G3 / 2, YA + EH / 2, '→', TEAL)
    for k, (_, label) in enumerate(D['training']):
        on = s >= k + 2
        last = k == len(D['training']) - 1
        dr.text((X3[k], YB3 - 10), fits(dr, label, F_HB, C3), font=F_HB, fill=(TEAL if last else INK) if on else GREY, anchor='ls')
        if on:
            framed(im, dr, ED_T[k], X3[k], YB3, *((TEAL, 4) if last else (GREY, 2)))
        else:
            placeholder(dr, X3[k], YB3, C3, EH)
        if on and k:
            badge(dr, X3[k] - G3 / 2, YB3 + EH / 2, '→', TEAL)
    box = (X3[3], YB3, X3[3] + C3 - 1, YB3 + EH - 1)
    if s >= 4:
        S = D['speed']
        rrect(dr, box, 12, fill=TEAL)
        x, y = box[0] + 18, box[1] + 40
        dr.text((x, y), S['title'], font=F_HB, fill=SOFT, anchor='ls'); y += 50
        dr.text((x, y), fits(dr, S['value'], F_NUM, C3 - 36), font=F_NUM, fill=WHITE, anchor='ls'); y += 34
        dr.text((x, y), fits(dr, S['sub'], F_HB, C3 - 36), font=F_HB, fill=WHITE, anchor='ls'); y += 40
        y = paragraph(dr, x, y, S['text'], F_HS, SOFT, C3 - 36, 23)
        assert y <= box[3] + 10, y
    else:
        placeholder(dr, *box[:2], C3, EH)
    line(dr, YB3 + EH + 52, D['messages'][s], F_MSG, TEAL if s in (1, 4) else INK)
    return im


# ---------------------------------------------------------------- scene 4: the masks (paper Fig. 2 and Fig. 9a)
K = V['masks']
C4, G4, LW4 = 240, 10, 226
X4 = [M + LW4 + 16 + k * (C4 + G4) for k in range(4)]
H4 = [round(C4 / r['aspect']) for r in K['rows']]
Y4 = [TOP + sum(H4[:i]) + 12 * i for i in range(len(H4))]
MASKS = [[load(f, (C4, H4[i])) for f in r['files']] for i, r in enumerate(K['rows'])]


def masks_frame(s):
    im, dr = canvas(3, K['head'], K['note'])
    for k, (title, col) in enumerate(K['columns']):
        dr.text((X4[k] + C4 / 2, TOP - 10), fits(dr, title, F_H, C4), font=F_H, fill=COL[col] if k <= s + 1 else GREY, anchor='ms')
    for i, r in enumerate(K['rows']):
        y = Y4[i] + 26
        y = paragraph(dr, M, y, r['task'], F_HB, INK, LW4, 23)
        dr.text((M, y + 4), r['baseline'], font=F_HS, fill=BASE, anchor='ls')
        if s >= 2:
            paragraph(dr, M, y + 40, r['effect'], F_HB, TEAL, LW4, 23)
        for k in range(4):
            if k <= s + 1:
                framed(im, dr, MASKS[i][k], X4[k], Y4[i], *((GREY, 2), (BASE, 3), (TEAL, 3), (TEAL, 3))[k])
            else:
                placeholder(dr, X4[k], Y4[i], C4, H4[i])
    line(dr, 900, K['messages'][s], F_MSG, TEAL if s == 2 else INK)
    return im


# ---------------------------------------------------------------- scene 5: the results (paper Fig. 10, Tables 1, 2, 5, 6)
R = V['results']
C5 = 198; G5 = (W - 2 * M - 6 * C5) / 5
X5 = [round(M + k * (C5 + G5)) for k in range(6)]
HE, HM = round(C5 * 237.4 * 0.81 / 359.6), round(C5 * 237.3 / 359.6)
YS, CARD_H = 262, 194
STRIP = [(load('fig10_edge_%s.%s' % (c[0], 'jpg' if c[0] == 'gt' else 'png'), (C5, HE)), load('fig10_mask_%s.png' % c[0], (C5, HM))) for c in R['columns']]


def results_frame(s):
    im, dr = canvas(4, R['head'], R['note'])
    dr.text((M, YS - 58), fits(dr, R['strip_title'], F_HS, W - 2 * M), font=F_HS, fill=MUTED, anchor='ls')
    y1 = YS + HE + 6 + HM + 26
    for k, (key, name, kind, ods, ap_) in enumerate(R['columns']):
        col = TEAL if key == 'trace' else MUTED if key == 'gt' else BASE
        cx = X5[k] + C5 / 2
        dr.text((cx, YS - 30), fits(dr, name, F_HB, C5), font=F_HB, fill=col, anchor='ms')
        dr.text((cx, YS - 10), fits(dr, kind, F_TICK, C5), font=F_TICK, fill=col, anchor='ms')
        framed(im, dr, STRIP[k][0], X5[k], YS, col if key != 'gt' else GREY, 3 if key == 'trace' else 2)
        framed(im, dr, STRIP[k][1], X5[k], YS + HE + 6, col if key != 'gt' else GREY, 3 if key == 'trace' else 2)
        for j, v in enumerate((ods, ap_)):
            if v is None:
                fits(dr, R['metrics'][j], F_HS, C5)
                rich(dr, cx, y1 + j * 28, R['metrics'][j], F_HS, F_HSUB, MUTED, anchor='m')
            else:
                dr.text((cx, y1 + j * 28), v, font=F('segoeuib.ttf', 22) if key == 'trace' else F('segoeui.ttf', 20), fill=TEAL if key == 'trace' else INK, anchor='ms')
    y = y1 + 28 + 36
    n = len(R['cards']); cw = (W - 2 * M - 16 * (n - 1)) / n
    for j, (value, metric, *desc) in enumerate(R['cards']):
        x = M + j * (cw + 16)
        if s < 1:
            placeholder(dr, x, y, cw, CARD_H)
            continue
        rrect(dr, (x, y, x + cw, y + CARD_H), 12, fill=TEAL_BG, outline=MINT_LINE)
        dr.text((x + cw / 2, y + 42), fits(dr, value, F_BIG, cw - 24), font=F_BIG, fill=TEAL, anchor='mm')
        dr.text((x + cw / 2, y + 86), fits(dr, metric, F_HB, cw - 24), font=F_HB, fill=INK, anchor='mm')
        for i, d in enumerate(desc):
            fits(dr, d, F_NOTE, cw - 20)
            rich(dr, x + cw / 2, y + 122 + i * 24, d, F_NOTE, F_HSUB, MUTED, anchor='m')
    line(dr, y + CARD_H + 50, R['line'] if s >= 1 else R['messages'][0], F_MSG, TEAL if s >= 1 else INK)
    return im


frames = []
add = lambda im, ms: frames.append((im, ms))
for s, ms in enumerate((1400, 2000, 1500, 1500, 2800)):
    add(observation_frame(s), ms)
for s, ms in enumerate((1500, 1100, 2200, 1100, 3400)):
    add(emergence_frame(s), ms)
for s, ms in enumerate((1500, 2400, 1100, 1100, 3400)):
    add(edge_frame(s), ms)
for s, ms in enumerate((1700, 1500, 3800)):
    add(masks_frame(s), ms)
for s, ms in enumerate((3600, 6200)):
    add(results_frame(s), ms)

# GIF palette: the flat UI colors and the main logo colors are reserved so text and logos stay clean; the rest of each frame is quantized.
def logo_colors(im, n=10):
    flat = Image.new('RGB', im.size, WHITE); flat.paste(im, (0, 0), im)
    p = flat.quantize(colors=n, method=Image.MEDIANCUT).getpalette()[:3 * n]
    return [tuple(p[i:i + 3]) for i in range(0, len(p), 3)]


RESERVED = list(dict.fromkeys([TEAL, TEAL_BG, MINT_LINE, INK, MUTED, LINE, WHITE, (0, 0, 0), GREY, TAB_DIM, BASE, SOFT]
                              + logo_colors(LOGO_L) + logo_colors(LOGO_R)))


def to_palette(f):
    k = len(RESERVED)
    q = f.quantize(colors=256 - k, method=Image.MEDIANCUT)
    p = (q.getpalette() or [])[:3 * (256 - k)]
    p = [v for c in RESERVED for v in c] + p + [0] * (3 * (256 - k) - len(p))
    pi = Image.new('P', (1, 1)); pi.putpalette(p)
    out = f.quantize(palette=pi, dither=Image.FLOYDSTEINBERG)
    idx, rgb = np.array(out), np.array(f.convert('RGB'))
    for j, col in enumerate(RESERVED):
        idx[(rgb == col).all(-1)] = j
    fixed = Image.frombytes('P', out.size, idx.astype(np.uint8).tobytes()); fixed.putpalette(p)
    return fixed


total_ms = sum(ms for _, ms in frames)
if args.preview:
    os.makedirs(args.preview, exist_ok=True)
    for i, (f, _) in enumerate(frames):
        f.save(os.path.join(args.preview, f'frame_{i:03d}.png'))
    json.dump([ms for _, ms in frames], open(os.path.join(args.preview, 'durations.json'), 'w'))
    print(f'{len(frames)} frames ({total_ms / 1000:.1f} s) written to {args.preview}')
else:
    before = open(args.out, 'rb').read() if os.path.exists(args.out) else None
    pal = [to_palette(f) for f, _ in frames]
    pal[0].save(args.out, save_all=True, append_images=pal[1:], duration=[ms for _, ms in frames], loop=0, optimize=True, disposal=1)
    after = open(args.out, 'rb').read()
    state = 'new file' if before is None else 'identical to the previous file' if before == after else 'differs from the previous file'
    print(f'{args.out}: {len(frames)} frames, {total_ms / 1000:.1f} s, {len(after) / 1e6:.1f} MB ({state})')
