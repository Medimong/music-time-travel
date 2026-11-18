"""data/ + queue/ -> site/ (흐름도·내 진도·회차별 읽기). 날짜가 안 된 회차는 페이지가 KST 오늘 날짜로 숨긴다."""
import glob, html, json, os, re, shutil, urllib.parse
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
esc = html.escape
d = json.load(open(f"{ROOT}/data/chronology.json"))
G = json.load(open(f"{ROOT}/data/genres.json"))
tops = list(G["_tops"])
nodes, edges = d["nodes"], d["edges"]
for n in nodes:
    n.setdefault("short", n["title"])

# ── 큐 회차를 미리 합친다 ──────────────────────────────
known = {n["id"] for n in nodes}
parts = []  # 회차별 읽기
for f in sorted(glob.glob(f"{ROOT}/queue/*.json")):
    q = json.load(open(f))
    for a in q["albums"]:
        top, sub = G.get(a["id"], [a.get("top"), a.get("sub")])
        if top and top not in tops:
            tops.append(top)
        if a["id"] not in known:
            known.add(a["id"])
            nodes.append({"id": a["id"], "year": q["year"], "title": a["title"], "artist": a["artist"],
                          "short": a.get("short", a["title"]), "status": "sent", "sendDate": q["date"],
                          "spotify": {"url": a["spotify"]}, "apple": {"url": a["apple"]}, "top": top, "sub": sub})
    have = {(e["from"], e["to"]) for e in edges}
    edges += [dict(e, sendDate=q["date"]) for e in q.get("edges", []) if (e["from"], e["to"]) not in have]
    parts.append({"part": q["part"], "year": q["year"], "d": q["date"], "label": f'{q["year"]}년 {q["partNo"]}/{q["partTotal"]}',
                  "title": q["title"], "albums": [a["id"] for a in q["albums"]],
                  "blocks": [{"t": "p", "x": q["intro"]}] + [b for e in q["essays"] for b in
                             ([{"t": "h", "x": e["heading"], "id": e["id"]}] + [{"t": "p", "x": p} for p in e["paras"]])]})

for n in nodes:
    g = G.get(n["id"])
    if g:
        n["top"], n["sub"] = g
    n.setdefault("top", "Rock"); n.setdefault("sub", "")
byid = {n["id"]: n for n in nodes}

# ── 지난 회차(1965~1973) 글 ─────────────────────────────
norm = lambda s: re.sub(r"[^a-z0-9가-힣]", "", s.lower().replace("’", "'"))
for f in sorted(glob.glob(f"{ROOT}/data/past/*.json")):
    p = json.load(open(f))
    ids = []
    for s in p.get("albums", []):
        t = norm(s.split("—")[-1])
        hit = [n["id"] for n in nodes if n["status"] == "sent" and n["year"] == p["year"] and t and (norm(n["title"]) in t or t in norm(n["title"]))]
        ids += [h for h in hit if h not in ids]
    if not ids:
        ids = [n["id"] for n in nodes if n["status"] == "sent" and n["year"] == p["year"] and not n.get("sendDate")]
    label = f'{p["year"]}년' + (f' {p["part"][-1]}/2' if "-P" in p["part"] else "")
    parts.append({"part": p["part"], "year": p["year"], "d": "", "label": label, "title": p.get("title", ""), "albums": ids, "blocks": p["blocks"]})
parts.sort(key=lambda x: (x["year"], x["part"]))
partof = {a: p["part"] for p in parts for a in p["albums"]}

# ── 배치 ───────────────────────────────────────────────
COL_W, NODE_W, NODE_H, LABEL_W, TOP = 168, 120, 140, 104, 56
years = sorted({n["year"] for n in nodes})
used = [t for t in tops if any(n["top"] == t for n in nodes)]
stack = defaultdict(list)
for n in nodes:
    stack[(n["top"], n["year"])].append(n)
rows = {t: max(len(stack[(t, y)]) for y in years) for t in used}
lane_y, y0 = {}, TOP
for t in used:
    lane_y[t] = y0 + 26  # 위 26px은 장르 이름표 자리
    y0 += rows[t] * NODE_H + 46
H, W = y0 + 10, LABEL_W + len(years) * COL_W + 40
pos = {}
for (t, y), ns in stack.items():
    for k, n in enumerate(ns):
        pos[n["id"]] = (LABEL_W + years.index(y) * COL_W + (COL_W - NODE_W) // 2, lane_y[t] + k * NODE_H)

svg = []
for e in edges:
    (x1, y1), (x2, y2) = pos[e["from"]], pos[e["to"]]
    sx, sy, tx, ty = x1 + NODE_W / 2, y1 + 40, x2 + NODE_W / 2, y2 + 40
    if sx != tx:
        sx, tx = (sx + 40, tx - 40) if tx > sx else (sx - 40, tx + 40)
    mx = (sx + tx) / 2
    cls = "doc" if e["type"] == "document" else "lis"
    svg.append(f'<path class="{cls}" data-d="{e.get("sendDate", "")}" data-f="{e["from"]}" data-t="{e["to"]}" '
               f'd="M{sx:.0f},{sy:.0f} C{mx:.0f},{sy:.0f} {mx:.0f},{ty:.0f} {tx:.0f},{ty:.0f}"/>')
cards = []
for n in nodes:
    x, y = pos[n["id"]]
    badge = '<em>수업</em>' if n["status"] == "sent" else ""
    cards.append(f'<button class="card" data-d="{n.get("sendDate", "")}" data-id="{n["id"]}" data-g="{esc(n["top"])}" style="left:{x}px;top:{y}px">'
                 f'<img src="covers/{n["id"]}.jpg" alt="" loading="lazy" width="80" height="80">{badge}'
                 f'<b>{esc(n["short"])}</b><span>{esc(n["artist"])}</span><i>{esc(n["sub"])}</i></button>')
firstd = {y: min((n.get("sendDate", "") for n in nodes if n["year"] == y), default="") for y in years}
heads = "".join(f'<div class="yr" data-d="{firstd[y]}" id="y{y}" style="left:{LABEL_W + i * COL_W}px">{y}</div>' for i, y in enumerate(years))
bands = "".join(f'<div class="band{" alt" if i % 2 else ""}" data-g="{esc(t)}" style="top:{lane_y[t] - 34}px;height:{rows[t] * NODE_H + 30}px"><span>{esc(t)}</span></div>' for i, t in enumerate(used))
nav = "".join(f'<a data-d="{firstd[y]}" href="#y{y}">{y}</a>' for y in years)
chips = "".join(f'<button class="chip" data-g="{esc(t)}">{esc(t)}</button>' for t in used)

rym = lambda n: "https://rateyourmusic.com/search?" + urllib.parse.urlencode({"searchtype": "l", "searchterm": f'{n["artist"]} {n["title"]}'})
meta = {n["id"]: {"t": n["title"], "a": n["artist"], "y": n["year"], "s": n["status"], "g": n["top"], "sub": n["sub"],
                  "sp": n.get("spotify", {}).get("url"), "ap": n.get("apple", {}).get("url"), "rym": rym(n),
                  "d": n.get("sendDate", ""), "p": partof.get(n["id"], "")} for n in nodes}
rel = defaultdict(list)
for e in edges:
    rel[e["from"]].append([e["to"], e["type"], e["label"], "out"])
    rel[e["to"]].append([e["from"], e["type"], e["label"], "in"])
DATA = json.dumps({"m": meta, "r": rel, "tops": used, "parts": parts}, ensure_ascii=False)

page = open(f"{ROOT}/scripts/site_template.html").read()
for k, v in {"__W__": str(W), "__H__": str(H), "__COLW__": str(COL_W), "__NODEW__": str(NODE_W), "__LABELW__": str(LABEL_W),
             "__BANDS__": bands, "__HEADS__": heads, "__SVG__": "".join(svg), "__CARDS__": "".join(cards),
             "__NAV__": nav, "__CHIPS__": chips, "__DATA__": DATA.replace("</", "<\\/")}.items():
    page = page.replace(k, v)

out = f"{ROOT}/site"
os.makedirs(out, exist_ok=True)
open(f"{out}/index.html", "w").write(page)
open(f"{out}/robots.txt", "w").write("User-agent: *\nDisallow: /\n")
shutil.copytree(f"{ROOT}/data/covers", f"{out}/covers", dirs_exist_ok=True)
print(f"site: {len(nodes)} nodes, {len(edges)} edges, {len(parts)} parts, {len(used)} genres, {W}x{H}px, {len(page)//1024}KB")
