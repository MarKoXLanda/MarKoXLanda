"""
VPet para el README de GitHub: Ame (o "Bit", la mini computadora)h.
Lee tu actividad publica reciente y dibuja assets/vpet.svg:
  - cada commit le da XP  -> sube de nivel cada 100
  - 5+ commits en 24 h      -> emocionada
  - commit en las ultimas 24 h -> feliz
  - 1 a 3 dias sin commits   -> tranquila
  - 4 a 9 dias sin commits   -> hambrienta
  - 10+ dias sin commits     -> dormida
Prueba local:  python pet/generate.py --demo happy
"""
import json, math, os, sys, urllib.request
from datetime import datetime, timezone, timedelta

USER = os.environ.get("GH_USER", "MarKoXLanda")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = os.environ.get("VPET_OUT", "assets/vpet.svg")
STATE = os.environ.get("VPET_STATE", "pet/state.json")
NAME = os.environ.get("VPET_NAME", "Ame")
CHARACTER = os.environ.get("VPET_CHARACTER", "ame")  # "ame" o "bit"


# ---------- datos ----------
def _get(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                               **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {})})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def fetch_events():
    """Actividad publica (incluye repos de organizaciones/equipos)."""
    events = []
    for page in (1, 2, 3):
        batch = _get(f"https://api.github.com/users/{USER}/events/public?per_page=100&page={page}")
        events += batch
        if len(batch) < 100:
            break
    return events


def fetch_repos():
    """Fecha del ultimo push de cada repo publico tuyo (respaldo por si la actividad no lo reporta)."""
    try:
        return _get(f"https://api.github.com/users/{USER}/repos?per_page=100&sort=pushed&type=owner")
    except Exception as e:  # si falla, seguimos solo con la actividad
        print("aviso: no se pudieron leer los repos:", e)
        return []


def _ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def summarize(events, state, repos=()):
    now = datetime.now(timezone.utc)
    seen = set(state.get("seen", []))
    last_push, new_commits, commits_24h = None, 0, 0
    fresh_repos = set()  # repos con push nuevo visto en la actividad
    for e in events:
        if e.get("type") != "PushEvent":
            continue
        t = _ts(e["created_at"])
        size = max(1, e.get("payload", {}).get("size", 1) or 1)
        last_push = max(last_push or t, t)
        if now - t < timedelta(hours=24):
            commits_24h += size
        if e["id"] not in seen:
            new_commits += size
            seen.add(e["id"])
            fresh_repos.add(e.get("repo", {}).get("name", "").split("/")[-1].lower())
    # respaldo: fecha de ultimo push de cada repo (sin contar el repo del perfil,
    # porque ahi el bot guarda a la mascota)
    prev = state.get("repos", {})
    current = {}
    for r in repos or ():
        name, pushed = r.get("name", ""), r.get("pushed_at")
        if not pushed or name.lower() == USER.lower():
            continue
        current[name] = pushed
        t = _ts(pushed)
        last_push = max(last_push or t, t)
        if name in prev and pushed != prev[name] and name.lower() not in fresh_repos:
            new_commits += 1
            if now - t < timedelta(hours=24):
                commits_24h += 1
    if current:
        state["repos"] = current
    state["seen"] = sorted(seen)[-500:]
    state["xp"] = state.get("xp", 0) + new_commits * 10
    if last_push and (not state.get("last_push") or last_push > _ts(state["last_push"])):
        state["last_push"] = last_push.isoformat()
    lp = state.get("last_push")
    days = (now - _ts(lp)).total_seconds() / 86400 if lp else 99
    return state, days, commits_24h


def mood_for(days, commits_24h):
    if commits_24h >= 5:
        return "excited"
    if days < 1:
        return "happy"
    if days < 4:
        return "ok"
    if days < 10:
        return "hungry"
    return "sleeping"


# ---------- dibujo ----------
P = 8  # tamaño de cada pixel

BIT = [
    "......L.........",
    ".....LlL........",
    "......S.........",
    ".OOOOOOOOOOOOOO.",
    ".OCCCCCCCCCCCCO.",
    ".OCOOOOOOOOOOCO.",
    ".OCOssssssssOCO.",
    ".OCOssssssssOCO.",
    ".OCOssssssssOCO.",
    ".OCOssssssssOCO.",
    ".OCOssssssssOCO.",
    ".OCOssssssssOCO.",
    ".OCOOOOOOOOOOCO.",
    ".OCCCCCCCCCrbCO.",
    ".OddddddddddddO.",
    "..OOOOOOOOOOOO..",
    "...OFO....OFO...",
    "...OOO....OOO...",
]

BASE = dict(O="#0D140C", C="#6B8E3D", d="#4A6B2A", L="#A6E36B", l="#D4F7A1",
            S="#3E6B23", b="#2F4F1E", F="#2F4F1E")
SCREEN = {"excited": "#0E2412", "happy": "#0B1F0F", "ok": "#0B1A0E",
          "hungry": "#1A1A0B", "sleeping": "#070D08"}
LED = {"excited": "#FFD166", "happy": "#7BC950", "ok": "#7BC950",
       "hungry": "#E8A33D", "sleeping": "#3E6B23"}
GLOW = {"excited": "#B8F28A", "happy": "#9BE06A", "ok": "#7BC950",
        "hungry": "#D9CC6A", "sleeping": "#4E8F2E"}
TEAR, PINK = "#8EC5E8", "#E58FA0"


def face(mood):
    """Pixeles de la cara dentro de la pantalla (x 4..11, y 6..11)."""
    eyes, mouth, extra = [], [], []
    if mood == "excited":   # ojos de estrella, boca abierta
        for cx in (5, 10):
            eyes += [(cx, 7), (cx - 1, 8), (cx, 8), (cx + 1, 8), (cx, 9)]
        mouth = [(7, 10), (8, 10), (7, 11), (8, 11)]
    elif mood == "happy":   # ^ ^
        eyes = [(4, 8), (5, 7), (6, 8), (9, 8), (10, 7), (11, 8)]
        mouth = [(6, 10), (7, 11), (8, 11), (9, 10)]
        extra = [(4, 10, PINK), (11, 10, PINK)]
    elif mood == "ok":      # o o con cursor parpadeante como boca
        eyes = [(5, 7), (5, 8), (10, 7), (10, 8)]
        mouth = [(7, 11), (8, 11)]
    elif mood == "hungry":  # ; ;
        eyes = [(4, 7), (5, 8), (11, 7), (10, 8)]
        mouth = [(6, 11), (7, 10), (8, 10), (9, 11)]
        extra = [(10, 9, TEAR), (10, 10, TEAR)]
    else:                   # - -
        eyes = [(4, 8), (5, 8), (6, 8), (9, 8), (10, 8), (11, 8)]
        mouth = [(8, 10)]
    return eyes, mouth, extra


def rect(x, y, c, extra=""):
    return f'<rect x="{x*P}" y="{y*P}" width="{P}" height="{P}" fill="{c}"{extra}/>'


def bit_sprite(mood):
    pal = dict(BASE, s=SCREEN[mood], r=LED[mood])
    out = [rect(x, y, pal[ch]) for y, row in enumerate(BIT) for x, ch in enumerate(row) if ch != "."]
    out.append(rect(2, 4, "#FFFFFF", ' opacity=".35"'))
    out.append(f'<rect x="{4*P}" y="{6*P}" width="{8*P}" height="{6*P}" fill="url(#scan)"/>')
    g = GLOW[mood]
    eyes, mouth, extra = face(mood)
    eyes_svg = "".join(rect(x, y, g) for x, y in eyes)
    out.append(f'<g class="blink">{eyes_svg}</g>' if mood in ("ok", "hungry") else eyes_svg)
    mouth_svg = "".join(rect(x, y, g) for x, y in mouth)
    out.append(f'<g class="cursor">{mouth_svg}</g>' if mood == "ok" else mouth_svg)
    out += [rect(x, y, c, ' opacity=".8"') for x, y, c in extra]
    out.append(rect(11, 13, LED[mood], ' class="led"'))
    return "".join(out)


# ---------- Ame ----------
CHAR_X0, CHAR_Y0 = 11, 2  # recorte usado (para coordenadas de la cara)
CHAR = [
    ".........aaaaaa...........",
    ".......aaccccccaa.........",
    ".....aaccccccacacca.......",
    "....acccccccccacccca......",
    "...acacaaccccccccccca.....",
    ".aacacaaccccecccccccca....",
    "..aaacacccceeacccaccca....",
    "...acacccceefaccccaccca...",
    "...acaccceeeffacccaccaaa..",
    "...acacceeeeffgaccaacca...",
    "..accacaaaefaaaaccffaca...",
    ".acccaahiffffiidccjfaca...",
    "aaaaccahiffffihhccjfaba...",
    "...accahkffffkkhccfla.....",
    "...accammfffffmmccaaa.....",
    "...accafffjjffffccaaaa....",
    "...accaafffffffacaa.......",
    ".....caaaaajjnaacooo......",
    ".....c..poojjjopppppo.....",
    ".....boopojffgopooooo.....",
    ".....oopofffffpoppppoo....",
    ".....oppoffjfooppppppo....",
    ".....oppqfjfopppppppppo...",
    ".....oopqojoqpppprpppppo..",
    "....opoppqoppqpqpropppppo.",
    "....opopppsppqqpproopppppo",
    "....opopptupppqppo..orpppo",
    "....oppoppvppppppo..opappo",
    "...opppoppuppppppo.opppppo",
    "...oppporrvrrrpppoopppppo.",
    "..oppppoppupprppwwwopppo..",
    ".oppppopppvpppowffwxopo...",
    ".oppppopppupppowfffxoo....",
    ".opppoopppvpppowwffwo.....",
    ".ooopooooooooooowwwo......",
    ".wfwooppprppppprooo.......",
    "wfffwoppprppppprppo.......",
    "wfwfoppppprpppppppoo......",
    "wffwopppppoopppppppo......",
    ".wwwopppppooppppppoo......",
    "....ooooppooopppoooo......",
    "....offgooo.oooofffo......",
    "....oyyfffo..offfyyo......",
    "....ooyyyyo..oyyoyyo......",
    "....oyoyyoo..ooyyoyo......",
    "....oyyyyo....oyyyyyo.....",
    "....oyyyyo.....oyyyyo.....",
    "....oyyoyo.....oyyyyo.....",
    "....oyoyyo......oyoyo.....",
    "....oyyyo.......oyyyyo....",
    "....oyyyo.......oyyyyo....",
    "...oooooo........oyyyo....",
    "...oapzzo........oooooo...",
    "...oppzzo........ozaazo...",
    "...oppzpo........ozppzo...",
    ".ooovzppo........ozpppo...",
    "ovvvvAvpo.........oBpppo..",
    "oBBBvAvCo.........oBBBBo..",
    "ooooooooo.........oooooo..",
]
CHAR_PAL = {'a': '#143463', 'b': '#837e82', 'c': '#041b3d', 'd': '#c3babf', 'e': '#e1ba3b', 'f': '#f9d5b1', 'g': '#f6d6bd', 'h': '#fbfbf9', 'i': '#285bc6', 'j': '#b9756a', 'k': '#269edb', 'l': '#b5252e', 'm': '#f8b9aa', 'n': '#bb7a76', 'o': '#05060a', 'p': '#313d3b', 'q': '#485454', 'r': '#232137', 's': '#c9ced1', 't': '#b4baba', 'u': '#969a99', 'v': '#6c706f', 'w': '#6f433a', 'x': '#754e47', 'y': '#91553b', 'z': '#ffd541', 'A': '#faa41b', 'B': '#77418d', 'C': '#7a3d80'}
CP = 3  # tamaño de pixel de Ame
SKIN, HAIR, MOUTH_C, BLUSH = "#f9d5b1", "#041b3d", "#b9756a", "#f8b9aa"
CYAN, YELLOW, WHITE, DARKM = "#269edb", "#ffd541", "#fbfbf9", "#6f433a"
EYES = [(18, 13), (18, 14), (18, 15), (19, 13), (19, 14), (19, 15),
        (24, 13), (25, 13), (24, 14), (25, 14), (26, 14), (24, 15), (25, 15), (26, 15)]


def char_face(mood):
    """Cambios sobre la cara original (coordenadas del sprite completo)."""
    f = {}
    if mood == "ok":
        return f
    if mood in ("happy", "sleeping"):
        f.update({p: SKIN for p in EYES})
        f[(21, 17)] = SKIN
    if mood == "happy":
        for x, y in [(18, 14), (19, 13), (20, 14), (24, 14), (25, 13), (26, 14)]:
            f[(x, y)] = HAIR
        f.update({(21, 17): MOUTH_C, (22, 17): MOUTH_C, (21, 18): BLUSH, (22, 18): BLUSH})
    elif mood == "sleeping":
        for x, y in [(18, 14), (19, 14), (24, 14), (25, 14), (26, 14)]:
            f[(x, y)] = HAIR
        f[(22, 17)] = MOUTH_C
    elif mood == "excited":
        f.update({(19, 14): YELLOW, (24, 14): YELLOW, (18, 13): YELLOW, (25, 13): YELLOW})
        f.update({(21, 17): DARKM, (22, 17): DARKM, (21, 18): BLUSH, (22, 18): DARKM})
    elif mood == "hungry":
        f.update({(18, 13): HAIR, (19, 13): HAIR, (24, 13): HAIR, (25, 13): HAIR})
        f.update({(21, 17): SKIN, (22, 17): SKIN})
        f.update({(20, 18): MOUTH_C, (21, 17): MOUTH_C, (22, 17): MOUTH_C, (23, 18): MOUTH_C})
        f.update({(26, 16): CYAN, (26, 17): CYAN})
    return f


def to_px(rows, x0=0, y0=0):
    return {(x0 + i, y0 + j): ch for j, r in enumerate(rows) for i, ch in enumerate(r) if ch != "."}


ORIG = to_px(CHAR)

# Torso sin brazos (filas 18-40), basado en el sprite original
TORSO_LR = [
    ".....c..poojjjopppppo.....",
    ".....boopojffgopooooo.....",
    ".....oopofffffpopppo......",
    ".....oppoffjfooppppo......",
    ".....oppqfjfoppppppo......",
    ".....oopqojoqppppro.......",
    "......oppqoppqpqpro.......",
    "......opppsppqqppro.......",
    "......opptupppqppo........",
    ".......oppvppppppo........",
    ".......oppuppppppo........",
    ".......orrvrrrpppo........",
    ".......oppupprpppo........",
    "......opppvppppppo........",
    "......opppuppppppo........",
    ".....oopppvppppppo........",
    ".....ooooooooooooo........",
    ".....oppprppppprooo.......",
    ".....oppprppppprppo.......",
    "....oppppprpppppppoo......",
    "....opppppoopppppppo......",
    "....opppppooppppppoo......",
    "....ooooppooopppoooo......",
]
# borde izquierdo del torso cuando se quita el brazo que cuelga
LEFT_EDGE = {24: 6, 25: 6, 26: 6, 27: 7, 28: 7, 29: 7, 30: 7, 31: 6, 32: 6, 33: 5, 34: 5,
             35: 5, 36: 5, 37: 4, 38: 4, 39: 4}
HANDS = {
    "fist_up": [".www.", "wfwfw", "wfwfw", "wfffw", ".wfw."],
    "open":    [".w.w.", "wfwfw", "wfwfww", "wffffw", "wfffw.", ".www.."],
    "flat":    [".www.", "wfffw", "wffxw", ".www."],
}
CLASP = [".wwwwww.", "wfffxffw", "wffwfffw", ".wwwwww."]
LEFT_BOOT = ["...oooooo", "...oapzzo", "...oppzzo", "...oppzpo", ".ooovzppo",
             "ovvvvAvpo", "oBBBvAvCo", "ooooooooo"]
FRONT_BOOT = ["oooooo.", "ozaazo.", "ozppzo.", "ozpppo.", ".oBpppo", ".oBBBBo", ".oooooo"]
KNEE_HI = "#b8774f"
BUBBLE = [  # burbujita al dormir (coordenadas de la cabeza)
    {(12, 15): "#8EC5E8"},
    {(12, 14): "#FFFFFF", (13, 14): "#8EC5E8", (12, 15): "#8EC5E8", (13, 15): "#8EC5E8"},
    {(13, 13): "#8EC5E8", (12, 14): "#8EC5E8", (13, 14): "#FFFFFF", (14, 14): "#8EC5E8",
     (13, 15): "#8EC5E8", (12, 15): "#D6F0FF", (14, 15): "#D6F0FF"},
    {(13, 12): "#8EC5E8", (14, 12): "#8EC5E8", (12, 13): "#8EC5E8", (13, 13): "#FFFFFF",
     (14, 13): "#D6F0FF", (15, 13): "#8EC5E8", (12, 14): "#8EC5E8", (13, 14): "#D6F0FF",
     (14, 14): "#D6F0FF", (15, 14): "#8EC5E8", (13, 15): "#8EC5E8", (14, 15): "#8EC5E8"},
]


def _seg(px, py, a, b):
    (ax, ay, ar), (bx, by, br) = a, b
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    t = 0 if l2 == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / l2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy)), ar + (br - ar) * t, t


def limb(c, pts, fill="p", lo="r", spots=None, behind=None, upto=1.0):
    """Brazo/pierna: puntos (x, y, grosor) con contorno de 1px y sombra.
    behind: pixeles (p. ej. el torso) que tapan la extremidad hasta la fraccion `upto`
    del recorrido, para que el hombro salga de atras del cuerpo y no del pecho."""
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    F, U = set(), {}
    n = len(pts) - 1
    for x in range(int(min(xs)) - 4, int(max(xs)) + 5):
        for y in range(int(min(ys)) - 4, int(max(ys)) + 5):
            for i in range(n):
                d, r, t = _seg(x, y, pts[i], pts[i + 1])
                if d <= r:
                    F.add((x, y)); U[(x, y)] = (i + t) / n
                    break
    hidden = (lambda q, u: q in behind and u <= upto) if behind else (lambda q, u: False)
    for x, y in F:
        for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if q not in F and not hidden(q, U[(x, y)]):
                c[q] = "o"
    for x, y in F:
        if hidden((x, y), U[(x, y)]):
            continue
        col = fill
        if lo and ((x + 1, y) not in F or (x, y + 1) not in F) and (x - 1, y) in F and (x, y - 1) in F:
            col = lo
        if spots and all(q in F for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))) \
                and (x * 3 + y * 5) % 6 == 0:
            col = spots
        c[(x, y)] = col


def stamp(c, art, x0, y0, flip=False):
    w = max(len(r) for r in art)
    for j, row in enumerate(art):
        row = row.ljust(w, ".")
        for i, ch in enumerate(row[::-1] if flip else row):
            if ch != ".":
                c[(x0 + i, y0 + j)] = ch


def face_px(mood):
    f = {(x - CHAR_X0, y - CHAR_Y0): col for (x, y), col in char_face(mood).items()}
    return {k: f.get(k, ch) for k, ch in ORIG.items()}


def head(px, dy=0):
    return {(x, y + dy): c for (x, y), c in px.items() if y <= 17}


def torso_lr():
    return to_px(TORSO_LR, 0, 18)


def torso_l():
    return {(x, y): c for (x, y), c in ORIG.items()
            if 18 <= y <= 40 and not (y in LEFT_EDGE and x < LEFT_EDGE[y])}


def legs_spread():
    """piernas abiertas para el brinco: inclina las medias y mueve las botas en bloque"""
    out = {}
    for (x, y), c in ORIG.items():
        if y < 41:
            continue
        left = x <= 11
        k = min(y, 50) - 41
        sh = (k + 1) // 3
        out[(x - sh if left else x + sh // 2, y)] = c
    return out


def arm(c, pts, body=None, upto=1.0):
    limb(c, pts, fill="p", lo="r", behind=body, upto=upto)


def ame_pose(mood, frame=0):
    """Devuelve (pixeles, desplazamiento_de_la_cabeza)."""
    F = face_px(mood)
    legs = {k: v for k, v in ORIG.items() if k[1] >= 41}
    if mood == "ok":
        return F, (0, 0)
    if mood == "excited":       # brazos arriba, piernas abiertas (brinco)
        T = torso_lr()
        c = {**T, **legs_spread(), **head(F)}
        arm(c, [(6.0, 21.5, 1.6), (2.5, 14.5, 1.7), (0.0, 8.5, 1.9)], T)
        arm(c, [(18.0, 21.5, 1.6), (21.5, 14.5, 1.7), (24.0, 8.5, 1.9)], T)
        stamp(c, HANDS["fist_up"], -2, 3)
        stamp(c, HANDS["fist_up"], 22, 3, flip=True)
        return c, (0, 0)
    if mood == "happy":         # saludando, mano en la cadera
        T = torso_l()
        c = {**T, **legs, **head(F)}
        if frame >= 0:
            wx = (-0.5, 1.5)[frame]
            arm(c, [(6.0, 21.5, 1.6), (0.5, 19.5, 1.7), (wx, 12.5, 1.9)], T)
            stamp(c, HANDS["open"], int(round(wx)) - 3, 6)
        return c, (0, 0)
    if mood == "hungry":        # manos en la panza, cabeza agachada
        T = torso_lr()
        c = {**T, **legs, **head(F, 1)}
        arm(c, [(6.0, 21.5, 1.6), (3.5, 27.5, 1.7), (8.5, 30.5, 1.8)], T, upto=0.5)
        arm(c, [(18.0, 21.5, 1.6), (20.5, 27.5, 1.7), (15.5, 30.5, 1.8)], T, upto=0.5)
        stamp(c, HANDS["flat"], 8, 29)
        stamp(c, HANDS["flat"], 12, 29, flip=True)
        return c, (0, 1)
    # sleeping: sentada abrazando sus rodillas
    T = {k: v for k, v in torso_lr().items() if k[1] <= 31}
    c = dict(T)
    limb(c, [(9, 23, 2.0), (9, 31, 1.6)], fill="y", lo=None, spots="o")
    limb(c, [(15, 23, 2.0), (15, 31, 1.6)], fill="y", lo=None, spots="o")
    stamp(c, FRONT_BOOT, 5, 31, flip=True)
    stamp(c, FRONT_BOOT, 13, 31)
    for kx in (8.6, 15.4):      # rodillas con brillo
        knee = {}
        limb(knee, [(kx, 22, 2.5), (kx + 0.01, 22.2, 2.5)], fill="y", lo="x", spots="o")
        for (x, y), col in knee.items():
            if col == "y" and (x - kx) + (y - 22) < -1.5 and knee.get((x - 1, y)) != "o" \
                    and knee.get((x, y - 1)) != "o":
                col = KNEE_HI
            c[(x, y)] = col
    arm(c, [(6.0, 21.5, 1.5), (3.5, 25.5, 1.6), (9.5, 27.5, 1.7)], T, upto=0.5)
    arm(c, [(18.0, 21.5, 1.5), (20.5, 25.5, 1.6), (14.5, 27.5, 1.7)], T, upto=0.5)
    stamp(c, CLASP, 8, 26)
    c.update(head(F))
    return c, (0, 0)


def _rects(px, ox, oy):
    """Une pixeles contiguos del mismo color en una fila para que el SVG pese menos."""
    out = []
    rows = {}
    for (x, y), c in px.items():
        rows.setdefault(y, []).append((x, c))
    for y, items in rows.items():
        items.sort()
        i = 0
        while i < len(items):
            x, c = items[i]
            j = i
            while j + 1 < len(items) and items[j + 1] == (items[j][0] + 1, c):
                j += 1
            col = c if c.startswith("#") else CHAR_PAL[c]
            out.append(f'<rect x="{(x+ox)*CP}" y="{(y+oy)*CP}" width="{(j-i+1)*CP}" height="{CP}" fill="{col}"/>')
            i = j + 1
    return "".join(out)


def ame_sprite(mood, cx=100, ground=192):
    """Grupo SVG completo de Ame (sombra + cuerpo + animaciones por cuadros)."""
    base, (hx, hy) = ame_pose(mood, -1 if mood == "happy" else 0)
    frames = []
    if mood == "happy":
        for f in (0, 1):
            full, _ = ame_pose(mood, f)
            frames.append({k: v for k, v in full.items() if base.get(k) != v})
    allpx = dict(base)
    for f in frames:
        allpx.update(f)
    minx = min(x for x, _ in allpx); maxx = max(x for x, _ in allpx)
    maxy = max(y for _, y in base)
    ox, oy = -minx, 0
    width = (maxx - minx + 1) * CP
    tx, ty = cx - width // 2, ground - (maxy + 1) * CP
    parts = [_rects(base, ox, oy)]
    for i, f in enumerate(frames):
        parts.append(f'<g class="fr fr{i}">{_rects(f, ox, oy)}</g>')
    if mood in ("ok", "hungry", "excited"):   # parpadeo
        lid = {(x - CHAR_X0 + hx, y - CHAR_Y0 + hy): (HAIR if y == 14 else SKIN) for x, y in EYES}
        parts.append(f'<g class="lid">{_rects(lid, ox, oy)}</g>')
    if mood == "sleeping":                    # burbujita
        for i, b in enumerate(BUBBLE):
            parts.append(f'<g class="bub b{i}" opacity=".9">{_rects(b, ox, oy)}</g>')
    rx = 40 if mood == "sleeping" else 30
    return (f'<g transform="translate({tx},{ty})">'
            f'<ellipse cx="{width // 2}" cy="{(maxy + 1) * CP - 1}" rx="{rx}" ry="4" fill="#000" opacity=".45" class="shadow"/>'
            f'<g class="pet">{"".join(parts)}</g></g>')


LABELS = {
    "ame": {
        "excited": "¡emocionada! · muchos commits hoy",
        "happy": "feliz · commit reciente",
        "ok": "tranquila · esperando tu código",
        "hungry": "hambrienta · ¡quiere commits!",
        "sleeping": "dormida · zzz",
    },
    "bit": {
        "excited": "¡emocionado! · muchos commits hoy",
        "happy": "feliz · commit reciente",
        "ok": "tranquilo · esperando tu código",
        "hungry": "hambriento · ¡quiere commits!",
        "sleeping": "dormido · zzz",
    },
}


def bar(x, y, label, value, color):
    w = 150
    fill = max(4, int(w * value))
    return (f'<text x="{x}" y="{y}" class="t s">{label}</text>'
            f'<rect x="{x}" y="{y+6}" width="{w}" height="10" rx="2" fill="#1B2A12"/>'
            f'<rect x="{x}" y="{y+6}" width="{fill}" height="10" rx="2" fill="{color}"/>')


# Efectos en pixel art (corazones, destellos, notas, zzz)
FX_ART = {
    "heart": ([".PP.PP.", "PWPPPPP", "PPPPPPP", ".PPPPP.", "..PPP..", "...P..."],
              {"P": "#E58FA0", "W": "#FFFFFF"}),
    "spark": (["...Y...", "...Y...", "..YWY..", "YYWWWYY", "..YWY..", "...Y...", "...Y..."],
              {"Y": "#FFD166", "W": "#FFF6D6"}),
    "spark_s": (["..Y..", ".YWY.", "YWWWY", ".YWY.", "..Y.."], {"Y": "#FFD166", "W": "#FFF6D6"}),
    "note": (["..G..", "..GG.", "..G.G", "..G..", "GGG..", "GGG..", ".G..."], {"G": "#A6E36B"}),
    "z": (["ZZZZ", "..Z.", ".Z..", "ZZZZ"], {"Z": "#A3B8A0"}),
    "Z": (["ZZZZZ", "...Z.", "..Z..", ".Z...", "ZZZZZ"], {"Z": "#A3B8A0"}),
    "dots": (["DD.DD.DD", "DD.DD.DD"], {"D": "#D9CC6A"}),
}
FXS = 3


def fx(kind, x, y, cls):
    art, pal = FX_ART[kind]
    rects = "".join(f'<rect x="{i*FXS}" y="{j*FXS}" width="{FXS}" height="{FXS}" fill="{pal[ch]}"/>'
                    for j, r in enumerate(art) for i, ch in enumerate(r) if ch != ".")
    return f'<g transform="translate({x},{y})"><g class="{cls}">{rects}</g></g>'


FX = {
    "ame": {
        "excited": fx("spark", 28, 30, "spark") + fx("spark", 160, 22, "spark s2") + fx("spark_s", 160, 96, "spark s3"),
        "happy": fx("heart", 24, 14, "heart") + fx("heart", 150, 44, "heart s2"),
        "ok": fx("note", 152, 40, "note"),
        "hungry": fx("dots", 146, 58, "q"),
        "sleeping": fx("z", 146, 88, "z") + fx("z", 158, 72, "z s2") + fx("Z", 170, 54, "z s3"),
    },
    "bit": {
        "excited": fx("spark", 150, 38, "spark") + fx("spark", 14, 48, "spark s2") + fx("spark_s", 162, 92, "spark s3"),
        "happy": fx("heart", 150, 40, "heart"),
        "ok": fx("note", 150, 30, "note"),
        "hungry": fx("dots", 148, 48, "q"),
        "sleeping": fx("z", 150, 46, "z") + fx("z", 162, 32, "z s2") + fx("Z", 174, 16, "z s3"),
    },
}
ANIM = {
    "ame": {"excited": ("hop", ".7s"), "happy": ("bob", "1.6s"), "ok": ("breathe", "3s"),
            "hungry": ("sag", "2.4s"), "sleeping": ("breathe", "4s")},
    "bit": {"excited": ("hop", ".6s"), "happy": ("hop", "1s"), "ok": ("squish", "2.4s"),
            "hungry": ("wobble", "1.6s"), "sleeping": ("breathe", "4s")},
}


def render(mood, level, xp_in_level, days):
    who = "bit" if CHARACTER == "bit" else "ame"
    happiness = {"excited": 1.0, "happy": .9, "ok": .65, "hungry": .3, "sleeping": .12}[mood]
    food = max(0.05, 1 - min(days, 10) / 10)
    anim, dur = ANIM[who][mood]
    label = LABELS[who][mood]
    if who == "bit":
        pet_group = ('<g transform="translate(26,22)"><ellipse cx="64" cy="146" rx="46" ry="5" fill="#000" '
                     f'opacity=".45" class="shadow"/><g class="pet">{bit_sprite(mood)}</g></g>')
    else:
        pet_group = ame_sprite(mood)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="460" height="200" viewBox="0 0 460 200" shape-rendering="crispEdges" role="img" aria-label="{NAME}, mascota virtual: {label}">
<defs>
  <pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">
    <rect width="4" height="2" fill="#000" opacity=".22"/>
  </pattern>
</defs>
<style>
  .t{{font-family:'Segoe UI',Ubuntu,'Helvetica Neue',sans-serif;fill:#E6EDF3}}
  .s{{font-size:11px;fill:#A3B8A0}}
  .h{{font-size:20px;font-weight:600}}
  .m{{font-size:12px;fill:#8FBC5A}}
  .pet{{animation:{anim} {dur} ease-in-out infinite;transform-box:fill-box;transform-origin:50% 100%}}
  .shadow{{animation:shadow {dur} ease-in-out infinite;transform-box:fill-box;transform-origin:center}}
  .blink{{animation:blink 4s infinite;transform-box:fill-box;transform-origin:center}}
  .cursor{{animation:cursor 1s steps(1) infinite}}
  .led{{animation:led 1.4s steps(1) infinite}}
  .lid{{opacity:0;animation:lid 4s steps(1) infinite}}
  .fr{{opacity:0}} .fr0{{animation:fr0 .9s steps(1) infinite}} .fr1{{animation:fr1 .9s steps(1) infinite}}
  .bub{{opacity:0}} .b0{{animation:b0 3.2s steps(1) infinite}} .b1{{animation:b1 3.2s steps(1) infinite}}
  .b2{{animation:b2 3.2s steps(1) infinite}} .b3{{animation:b3 3.2s steps(1) infinite}}
  @keyframes hop{{0%,100%{{transform:translateY(0) scale(1,1)}}15%{{transform:translateY(0) scale(1.06,.92)}}45%{{transform:translateY(-12px) scale(.97,1.03)}}75%{{transform:translateY(0) scale(1.04,.95)}}}}
  @keyframes bob{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-3px)}}}}
  @keyframes sag{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(2px)}}}}
  @keyframes squish{{0%,100%{{transform:scale(1,1)}}50%{{transform:scale(1.05,.93)}}}}
  @keyframes wobble{{0%,100%{{transform:rotate(0)}}25%{{transform:rotate(-3deg)}}75%{{transform:rotate(3deg)}}}}
  @keyframes breathe{{0%,100%{{transform:scale(1,1)}}50%{{transform:scale(1.02,.97)}}}}
  @keyframes shadow{{0%,100%{{transform:scaleX(1)}}45%{{transform:scaleX(.8)}}}}
  @keyframes blink{{0%,92%,100%{{transform:scaleY(1)}}95%{{transform:scaleY(.1)}}}}
  @keyframes cursor{{0%{{opacity:1}}50%{{opacity:0}}}}
  @keyframes led{{0%{{opacity:1}}50%{{opacity:.35}}}}
  @keyframes lid{{0%{{opacity:0}}94%{{opacity:1}}97%{{opacity:0}}}}
  @keyframes fr0{{0%{{opacity:1}}50%{{opacity:0}}}}
  @keyframes fr1{{0%{{opacity:0}}50%{{opacity:1}}}}
  @keyframes b0{{0%{{opacity:.9}}25%{{opacity:0}}}}
  @keyframes b1{{0%{{opacity:0}}25%{{opacity:.9}}50%{{opacity:0}}}}
  @keyframes b2{{0%{{opacity:0}}50%{{opacity:.9}}75%{{opacity:0}}}}
  @keyframes b3{{0%{{opacity:0}}75%{{opacity:.9}}100%{{opacity:0}}}}
  @keyframes float{{0%{{opacity:0;transform:translateY(6px)}}50%{{opacity:1}}100%{{opacity:0;transform:translateY(-8px)}}}}
  .z{{animation:float 3s infinite}}
  .heart{{animation:float 1.8s infinite}}
  .spark{{animation:float 1.2s infinite}}
  .q{{animation:float 2s infinite}}
  .note{{animation:float 3s infinite}}
  .s2{{animation-delay:-.6s}} .s3{{animation-delay:-1.2s}}
</style>
<rect width="460" height="200" rx="10" fill="#0D1117" stroke="#2F4F1E"/>
{pet_group}
{FX[who][mood]}
<g transform="translate(200,18)">
  <text x="0" y="38" class="t h">{NAME} <tspan class="m">Lv. {level}</tspan></text>
  <text x="0" y="58" class="t m">{label}</text>
  {bar(0, 80, "felicidad", happiness, "#7BC950")}
  {bar(0, 108, "comida (commits)", food, "#B5A85A")}
  {bar(0, 136, f"xp {xp_in_level}/100", xp_in_level / 100, "#6B8E3D")}
</g>
</svg>'''


def main():
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    if "--demo" in sys.argv:
        mood = sys.argv[sys.argv.index("--demo") + 1]
        days = {"excited": .1, "happy": .2, "ok": 2, "hungry": 6, "sleeping": 15}[mood]
        svg = render(mood, 7, 40, days)
    else:
        state = json.load(open(STATE)) if os.path.exists(STATE) else {}
        state, days, c24 = summarize(fetch_events(), state, fetch_repos())
        xp = state["xp"]
        svg = render(mood_for(days, c24), 1 + xp // 100, xp % 100, days)
        os.makedirs(os.path.dirname(STATE) or ".", exist_ok=True)
        json.dump(state, open(STATE, "w"), indent=1)
    open(OUT, "w", encoding="utf-8").write(svg)
    print("wrote", OUT)


if __name__ == "__main__":
    main()