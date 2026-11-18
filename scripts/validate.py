"""큐 원고 검사. 사용: python3 scripts/validate.py [--offline]
--offline 이면 네트워크 확인(링크·Apple 한국 스토어)을 건너뛴다."""
import json, os, re, sys, urllib.request, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OFFLINE = "--offline" in sys.argv
BANNED = re.compile(r"[—→←↔⇒✅❌⭐🎵]|--")
errs = []
chron = json.load(open(f"{ROOT}/data/chronology.json"))
known = {n["id"] for n in chron["nodes"]}
sent_ids = {n["id"] for n in chron["nodes"] if n["status"] == "sent"}
G = json.load(open(f"{ROOT}/data/genres.json"))
tops = G["_tops"]
log = json.load(open(f"{ROOT}/sent-log.json")) if os.path.exists(f"{ROOT}/sent-log.json") else {}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 music-time-travel-validator"})
    return urllib.request.urlopen(req, timeout=20)


def text_of(q):
    yield q["title"]; yield q["intro"]
    for a in q["albums"]:
        yield a["blurb"]
    for e in q["essays"]:
        yield e["heading"]; yield from e["paras"]


files = sorted(f for f in os.listdir(f"{ROOT}/queue") if f.endswith(".json"))
for f in files:
    q = json.load(open(f"{ROOT}/queue/{f}"))
    E = lambda m: errs.append(f"{f}: {m}")
    if q["date"] != f[:10]: E("date와 파일명 불일치")
    if all(f"{q['part']}|{w}" in log for w in ("gihun", "junghun")):
        known |= {a["id"] for a in q["albums"]}; continue  # 이미 보낸 회차
    ids = [a["id"] for a in q["albums"]]
    if len(ids) < 2: E("앨범이 2장 미만")
    if len(ids) < 3 and "두 장" not in q["intro"]: E("2장인 날은 intro에 이유를 적을 것")
    for a in q["albums"]:
        for k in ("id", "artist", "title", "released", "genre", "blurb", "length", "spotify", "apple"):
            if not a.get(k): E(f"{a.get('id')} {k} 없음")
        if a["id"] in sent_ids: E(f"{a['id']} 이미 수업에서 보낸 음반")
        top, sub = G.get(a["id"], [a.get("top"), a.get("sub")])
        if top not in tops: E(f"{a['id']} 상위 장르 top '{top}'가 data/genres.json의 _tops에 없음")
        if not sub: E(f"{a['id']} 세부장르 sub 없음")
        if not os.path.exists(f"{ROOT}/data/covers/{a['id']}.jpg"): E(f"{a['id']} 커버 없음")
        if not re.match(r"https://open\.spotify\.com/album/[A-Za-z0-9]{22}$", a["spotify"]): E(f"{a['id']} spotify 형식")
        m = re.match(r"https://music\.apple\.com/kr/album/(\d+)$", a["apple"])
        if not m: E(f"{a['id']} apple 형식(kr 스토어)")
        if not OFFLINE:
            try:
                t = json.load(get("https://open.spotify.com/oembed?url=" + a["spotify"]))["title"]
                if a["title"].lower()[:8] not in t.lower(): E(f"{a['id']} spotify 제목 불일치: {t}")
            except Exception as x: E(f"{a['id']} spotify 확인 실패 {x}")
            if m and not json.load(get(f"https://itunes.apple.com/lookup?id={m[1]}&country=kr"))["results"]:
                E(f"{a['id']} 한국 Apple Music에 없음")
    if sorted(e["id"] for e in q["essays"]) != sorted(ids): E("에세이와 앨범 목록 불일치")
    for t in text_of(q):
        if BANNED.search(t): E(f"금지 부호: {BANNED.search(t)[0]!r} in {t[:30]}")
    for e in q["essays"]:
        n = sum(len(p) for p in e["paras"])
        if not 450 <= n <= 1400: E(f"{e['id']} 에세이 길이 {n}자")
    known |= set(ids)
    for e in q.get("edges", []):
        if e["from"] not in known or e["to"] not in known: E(f"연결 대상 없음 {e['from']}→{e['to']}")
        if e["type"] == "document" and not e.get("source"): E("document 연결에 source 없음")
    if not 3 <= len(q["readings"]) <= 5: E("읽을거리 3–5개")
    if not OFFLINE:
        for r in q["readings"]:
            try: get(r["url"])
            except Exception as x: E(f"읽을거리 열리지 않음 {r['url']} {x}")
    print(f"checked {f} ({q['part']})")

print("\n".join(errs) if errs else "OK")
sys.exit(1 if errs else 0)
