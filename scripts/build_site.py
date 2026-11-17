"""data/chronology.json -> site/index.html
흐름도(위치·연결선은 여기서 계산) + 기훈/정훈 선택 + 들었음 체크(Firestore) + Spotify/Apple/RYM 링크."""
import html, json, os, shutil, urllib.parse
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = json.load(open(f"{ROOT}/data/chronology.json"))
nodes, edges, lanes = d["nodes"], d["edges"], d["lanes"]
# 아직 날짜가 안 된 큐 회차도 미리 넣어 두고, 페이지가 오늘 날짜(KST)를 보고 보여 준다.
import glob
known = {n["id"] for n in nodes}
for f in sorted(glob.glob(f"{ROOT}/queue/*.json")):
    q = json.load(open(f))
    for ln in q.get("lanes", []):
        if ln not in lanes: lanes.append(ln)
    for a in q["albums"]:
        if a["id"] in known: continue
        known.add(a["id"])
        nodes.append({"id": a["id"], "year": q["year"], "title": a["title"], "artist": a["artist"], "short": a.get("short", a["title"]),
                      "lane": lanes.index(a["lane"]), "status": "sent", "sendDate": q["date"],
                      "spotify": {"url": a["spotify"]}, "apple": {"url": a["apple"]}})
    have = {(e["from"], e["to"]) for e in edges}
    edges += [dict(e, sendDate=q["date"]) for e in q.get("edges", []) if (e["from"], e["to"]) not in have]

COL_W, NODE_W, NODE_H, LABEL_W, TOP = 168, 120, 132, 96, 56
years = sorted({n["year"] for n in nodes})
byid = {n["id"]: n for n in nodes}

stack = defaultdict(list)
for n in nodes:
    stack[(n["lane"], n["year"])].append(n)
lane_rows = [max([len(stack[(i, y)]) for y in years] + [1]) for i in range(len(lanes))]
lane_y, y0 = [], TOP
for rows in lane_rows:
    lane_y.append(y0)
    y0 += rows * NODE_H + 20
H, W = y0 + 10, LABEL_W + len(years) * COL_W + 20

pos = {}
for (lane, year), ns in stack.items():
    for k, n in enumerate(ns):
        pos[n["id"]] = (LABEL_W + years.index(year) * COL_W + (COL_W - NODE_W) // 2, lane_y[lane] + k * NODE_H)

esc = html.escape
svg = []
for e in edges:
    (x1, y1), (x2, y2) = pos[e["from"]], pos[e["to"]]
    sx, sy, tx, ty = x1 + NODE_W / 2, y1 + 40, x2 + NODE_W / 2, y2 + 40
    if sx != tx:
        sx, tx = (sx + 40, tx - 40) if tx > sx else (sx - 40, tx + 40)
    mx = (sx + tx) / 2
    cls = "doc" if e["type"] == "document" else "lis"
    svg.append(f'<path class="{cls}" data-d="{e.get("sendDate","")}" data-f="{e["from"]}" data-t="{e["to"]}" d="M{sx:.0f},{sy:.0f} C{mx:.0f},{sy:.0f} {mx:.0f},{ty:.0f} {tx:.0f},{ty:.0f}"/>')

cards = []
for n in nodes:
    x, y = pos[n["id"]]
    badge = '<em>수업</em>' if n["status"] == "sent" else ""
    cards.append(f'<button class="card" data-d="{n.get("sendDate","")}" data-id="{n["id"]}" style="left:{x}px;top:{y}px">'
                 f'<img src="covers/{n["id"]}.jpg" alt="" loading="lazy" width="80" height="80">{badge}'
                 f'<b>{esc(n["short"])}</b><span>{esc(n["artist"])}</span></button>')

firstd = {y: min((n.get("sendDate","") for n in nodes if n["year"] == y), default="") for y in years}
heads = "".join(f'<div class="yr" data-d="{firstd[y]}" id="y{y}" style="left:{LABEL_W + i * COL_W}px">{y}</div>' for i, y in enumerate(years))
lanelbl = "".join(f'<div class="ln" style="top:{lane_y[i]}px;height:{lane_rows[i] * NODE_H}px">{esc(l)}</div>' for i, l in enumerate(lanes))
bands = "".join(f'<div class="band" style="top:{lane_y[i] - 8}px;height:{lane_rows[i] * NODE_H + 4}px"></div>' for i in range(len(lanes)) if i % 2 == 0)
nav = "".join(f'<a data-d="{firstd[y]}" href="#y{y}">{y}</a>' for y in years)

def rym(n):
    return "https://rateyourmusic.com/search?" + urllib.parse.urlencode({"searchtype": "l", "searchterm": f'{n["artist"]} {n["title"]}'})

meta = {n["id"]: {"t": n["title"], "a": n["artist"], "y": n["year"], "s": n["status"],
                  "sp": n.get("spotify", {}).get("url"), "ap": n.get("apple", {}).get("url"),
                  "rym": n.get("rym") or rym(n), "part": n.get("part"), "d": n.get("sendDate", "")} for n in nodes}
rel = defaultdict(list)
for e in edges:
    rel[e["from"]].append([e["to"], e["type"], e["label"], "out"])
    rel[e["to"]].append([e["from"], e["type"], e["label"], "in"])
DATA = json.dumps({"m": meta, "r": rel}, ensure_ascii=False)
n_sent = sum(n["status"] == "sent" for n in nodes)

page = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow">
<title>대중음악 시간여행</title>
<style>
:root{{--bg:#f6f4ee;--fg:#222;--mute:#8a8a8a;--line:#c9c2b3;--doc:#c2410c;--card:#fff;--band:#efebe2;--acc:#2f6f4f;--hi:#d97706}}
@media (prefers-color-scheme:dark){{:root{{--bg:#16181b;--fg:#e8e6e1;--mute:#8d8d8d;--line:#4a4844;--doc:#f08a4b;--card:#23262a;--band:#1d2023;--acc:#7cc39c;--hi:#fbbf24}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font-family:-apple-system,'Apple SD Gothic Neo','Noto Sans KR',sans-serif}}
header{{padding:18px 16px 6px}}h1{{margin:0 0 4px;font-size:23px}}header p{{margin:3px 0;color:var(--mute);font-size:14px;line-height:1.5}}
.who{{display:flex;gap:8px;align-items:center;margin:10px 0 4px;flex-wrap:wrap}}.who button{{font:inherit;font-size:15px;padding:6px 14px;border-radius:18px;border:1.5px solid var(--line);background:var(--card);color:var(--fg);cursor:pointer}}
.who button.on{{background:var(--acc);border-color:var(--acc);color:#fff;font-weight:700}}#prog{{font-size:14px;color:var(--mute)}}
.nav{{display:flex;flex-wrap:wrap;gap:6px;padding:6px 16px 8px}}.nav a{{font-size:13px;color:var(--fg);text-decoration:none;border:1px solid var(--line);border-radius:12px;padding:2px 9px}}
.legend{{font-size:13px;color:var(--mute);padding:0 16px 8px;display:flex;gap:14px;flex-wrap:wrap}}.legend i{{display:inline-block;width:24px;border-top:2px solid var(--doc);vertical-align:middle;margin-right:4px}}.legend i.l{{border-top:2px dashed var(--mute)}}
.scroll{{overflow-x:auto;-webkit-overflow-scrolling:touch;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}}
.chart{{position:relative;width:{W}px;height:{H}px}}svg{{position:absolute;inset:0}}
path{{fill:none;stroke-width:1.5}}path.lis{{stroke:var(--line);stroke-dasharray:5 5}}path.doc{{stroke:var(--doc);stroke-width:2.2}}
path.hl{{stroke:var(--hi);stroke-width:3;stroke-dasharray:none}}
.band{{position:absolute;left:0;right:0;background:var(--band)}}
.yr{{position:absolute;top:16px;width:{COL_W}px;text-align:center;font-weight:700;font-size:18px}}
.ln{{position:absolute;left:0;width:{LABEL_W - 6}px;padding:6px;font-size:12px;color:var(--mute);display:flex;align-items:center}}
.card{{position:absolute;width:{NODE_W}px;text-align:center;color:var(--fg);background:none;border:0;padding:0;font:inherit;cursor:pointer}}
.card img{{width:80px;height:80px;border-radius:6px;display:block;margin:0 auto 4px;object-fit:cover;opacity:.32;filter:grayscale(.85);transition:.2s}}
.card.done img{{opacity:1;filter:none;box-shadow:0 0 0 3px var(--acc)}}.card.sel img{{box-shadow:0 0 0 3px var(--hi)}}
.card em{{position:absolute;top:2px;left:22px;font-style:normal;font-size:10px;background:var(--fg);color:var(--bg);border-radius:3px;padding:0 4px}}
.card b{{display:block;font-size:12px;line-height:1.25;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}.card span{{display:block;font-size:11px;color:var(--mute);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.card:not(.done) b{{color:var(--mute);font-weight:500}}
#sheet{{position:fixed;left:0;right:0;bottom:0;background:var(--card);border-top:1px solid var(--line);box-shadow:0 -6px 24px rgba(0,0,0,.15);padding:16px;max-height:62vh;overflow:auto;transform:translateY(105%);transition:.25s;z-index:9}}
#sheet.open{{transform:none}}.sh{{display:flex;gap:14px;align-items:flex-start;max-width:720px;margin:0 auto}}.sh img{{width:96px;height:96px;border-radius:8px;flex:none}}
.sh h2{{margin:0 0 2px;font-size:18px}}.sh .sub{{color:var(--mute);font-size:14px;margin-bottom:10px}}
.acts{{display:flex;gap:8px;flex-wrap:wrap}}.acts a,.acts button{{font:inherit;font-size:14px;padding:7px 12px;border-radius:8px;border:1px solid var(--line);background:var(--bg);color:var(--fg);text-decoration:none;cursor:pointer}}
.acts .chk.on{{background:var(--acc);border-color:var(--acc);color:#fff;font-weight:700}}.other{{font-size:13px;color:var(--mute);margin-top:8px}}
.rels{{max-width:720px;margin:12px auto 0;padding:0;list-style:none;font-size:13px;color:var(--mute)}}.rels li{{margin:4px 0;line-height:1.45}}
#x{{position:absolute;top:8px;right:12px;border:0;background:none;font-size:22px;color:var(--mute);cursor:pointer}}
#gate{{position:fixed;inset:0;background:var(--bg);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;z-index:20}}#gate.hide{{display:none}}
#gate button{{font:inherit;font-size:20px;padding:14px 40px;border-radius:14px;border:1.5px solid var(--line);background:var(--card);color:var(--fg);cursor:pointer;min-width:200px}}
#err{{color:var(--doc);font-size:13px;padding:0 16px}}
</style></head><body>
<div id="gate"><h1>누구세요?</h1><button data-u="gihun">기훈</button><button data-u="junghun">정훈</button></div>
<header><h1>대중음악 시간여행</h1>
<p>1965년부터 발매 순서대로 듣는 음악사 흐름도. <span id="cnt"></span> 표지를 누르면 듣기·RYM·들었음 체크.</p>
<div class="who"><button data-u="gihun">기훈</button><button data-u="junghun">정훈</button><span id="prog"></span></div></header>
<div class="legend"><span>진한 표지 = 들음 · 옅은 표지 = 아직</span><span><i></i>근거 있는 직접 관계</span><span><i class="l"></i>이어 들어볼 경로</span></div>
<nav class="nav">{nav}</nav><div id="err"></div>
<div class="scroll" id="sc"><div class="chart">{bands}{heads}<svg width="{W}" height="{H}">{"".join(svg)}</svg>{lanelbl}{"".join(cards)}</div></div>
<div style="height:70vh"></div>
<div id="sheet"><button id="x" aria-label="닫기">×</button><div class="sh"><img id="si" alt=""><div><h2 id="st"></h2><div class="sub" id="ss"></div>
<div class="acts"><button class="chk" id="sc2">들었음</button><a id="sl" target="_blank" rel="noopener"></a><a id="sr" target="_blank" rel="noopener">RYM</a></div><div class="other" id="so"></div></div></div><ul class="rels" id="srel"></ul></div>
<script type="module">
import {{initializeApp}} from 'https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js';
import {{getFirestore,doc,onSnapshot,setDoc,updateDoc,deleteField,serverTimestamp}} from 'https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js';
const D={DATA};
const NAME={{gihun:'기훈',junghun:'정훈'}}, OTHER={{gihun:'junghun',junghun:'gihun'}};
const db=getFirestore(initializeApp({{apiKey:'AIzaSyAtUfasA-8gg2qZb0IFz8to10_yEc_Gd6U',authDomain:'music-time-travel-gk.firebaseapp.com',projectId:'music-time-travel-gk',appId:'1:634754441954:web:9e5f699f12706d4c1074bb'}}));
const TODAY=new Date(Date.now()+9*3600e3).toISOString().slice(0,10);
const live=id=>!D.m[id].d||D.m[id].d<=TODAY;
document.querySelectorAll('[data-d]').forEach(el=>{{const x=el.dataset.d;if(x&&x>TODAY)el.style.display='none'}});
for(const k of Object.keys(D.m))if(!live(k))delete D.m[k];
for(const k of Object.keys(D.r))D.r[k]=(D.r[k]||[]).filter(r=>D.m[r[0]]);
const S={{gihun:{{}},junghun:{{}}}}; let me=null, cur=null;
try{{me=localStorage.getItem('mtt_who')}}catch(e){{}}
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
function pick(u){{me=u;try{{localStorage.setItem('mtt_who',u)}}catch(e){{}};$('#gate').classList.add('hide');paint();if(cur)open(cur)}}
$$('[data-u]').forEach(b=>b.onclick=()=>pick(b.dataset.u));
if(me&&NAME[me])pick(me);
for(const u of ['gihun','junghun'])onSnapshot(doc(db,'listen',u),s=>{{S[u]=(s.data()||{{}}).a||{{}};paint();if(cur)open(cur)}},e=>$('#err').textContent='기록을 불러오지 못했습니다: '+e.code);
function paint(){{
  $$('.who button').forEach(b=>b.classList.toggle('on',b.dataset.u===me));
  const ids0=Object.keys(D.m);document.getElementById('cnt').textContent=`수업 ${{ids0.filter(i=>D.m[i].s==='sent').length}}장 · 전체 ${{ids0.length}}장`;
  if(!me)return; const a=S[me];
  $$('.card').forEach(c=>c.classList.toggle('done',!!a[c.dataset.id]));
  const ids=Object.keys(D.m), lec=ids.filter(i=>D.m[i].s==='sent');
  $('#prog').textContent=`${{NAME[me]}}: 수업 ${{lec.filter(i=>a[i]).length}}/${{lec.length}}장 · 전체 ${{ids.filter(i=>a[i]).length}}/${{ids.length}}장 들음`;
}}
function open(id){{
  cur=id; const m=D.m[id], mine=!!(me&&S[me][id]);
  $$('.card').forEach(c=>c.classList.toggle('sel',c.dataset.id===id));
  $$('path').forEach(p=>p.classList.toggle('hl',p.dataset.f===id||p.dataset.t===id));
  $('#si').src='covers/'+id+'.jpg'; $('#st').textContent=m.t; $('#ss').textContent=`${{m.a}} · ${{m.y}}`+(m.s==='sent'?' · 수업 음반':' · 맥락 음반');
  const c=$('#sc2'); c.classList.toggle('on',mine); c.textContent=mine?'✓ 들었음':'들었음 체크';
  const ap=me==='junghun', url=ap?(m.ap||m.sp):(m.sp||m.ap);
  $('#sl').textContent=ap?'Apple Music에서 듣기':'Spotify에서 듣기'; $('#sl').href=url||'#'; $('#sl').style.display=url?'':'none';
  $('#sr').href=m.rym;
  const o=me&&OTHER[me]; $('#so').textContent=o?`${{NAME[o]}}: ${{S[o][id]?'들었음 ✓':'아직'}}`:'';
  $('#srel').innerHTML=(D.r[id]||[]).map(([j,t,l,dir])=>`<li>${{dir==='in'?D.m[j].t+' ('+D.m[j].y+') →':'→ '+D.m[j].t+' ('+D.m[j].y+')'}} ${{t==='document'?'━':'┄'}} ${{l.replace(/</g,'&lt;')}}</li>`).join('');
  $('#sheet').classList.add('open');
}}
$$('.card').forEach(c=>c.onclick=()=>open(c.dataset.id));
paint();
$('#x').onclick=()=>{{$('#sheet').classList.remove('open');cur=null;$$('.card').forEach(c=>c.classList.remove('sel'));$$('path').forEach(p=>p.classList.remove('hl'))}};
$('#sc2').onclick=async()=>{{
  if(!me||!cur)return; const ref=doc(db,'listen',me), on=!S[me][cur];
  try{{ if(on) await setDoc(ref,{{a:{{[cur]:Date.now()}},at:serverTimestamp()}},{{merge:true}});
        else await updateDoc(ref,{{['a.'+cur]:deleteField(),at:serverTimestamp()}}); }}
  catch(e){{$('#err').textContent='저장 실패: '+e.code}}
}};
// 첫 화면은 가장 최근 연도로
addEventListener('load',()=>{{const v=[...document.querySelectorAll('.yr')].filter(e=>e.style.display!=='none').pop();if(v)$('#sc').scrollLeft=v.offsetLeft-200}});
</script>
</body></html>"""

out = f"{ROOT}/site"
os.makedirs(out, exist_ok=True)
open(f"{out}/index.html", "w").write(page)
open(f"{out}/robots.txt", "w").write("User-agent: *\nDisallow: /\n")
shutil.copytree(f"{ROOT}/data/covers", f"{out}/covers", dirs_exist_ok=True)
print(f"site: {len(nodes)} nodes, {len(edges)} edges, {W}x{H}px, {len(page)//1024}KB")
