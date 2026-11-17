"""매일 00:00 KST 발송기. AI 없이 큐에 있는 원고만 보낸다.

- queue/<YYYY-MM-DD>.json 중 오늘(KST) 이하로 아직 안 보낸 가장 이른 회차 하나를 보낸다(밀린 날은 하나씩 따라잡음).
- 중복 방지: sent-log.json 의 "<part>|<who>" 키. 보낸 직후 기록·commit·push.
- 두 사람 모두 보내지면 연표에 반영(sent 승격, 새 노드·연결 추가).
- 남은 원고가 3일치 미만이면 경고 메일.
환경변수: SMTP_USER SMTP_PASS TO_GIHUN TO_JUNGHUN [ALERT_TO] [MODE=test TEST_TO=...]
"""
import datetime as dt, html, json, os, smtplib, subprocess, sys, time
from email.mime.text import MIMEText
from email.utils import formataddr
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KST = ZoneInfo("Asia/Seoul")
REPO_RAW = "https://raw.githubusercontent.com/Medimong/music-time-travel/main/data/covers"
SITE = "https://medimong.github.io/music-time-travel/"
SVC = {"gihun": ("spotify", "Spotify", "#1DB954"), "junghun": ("apple", "Apple Music", "#FA243C")}
esc = html.escape


def load(p, default=None):
    p = f"{ROOT}/{p}"
    return json.load(open(p)) if os.path.exists(p) else default


def save(p, obj):
    json.dump(obj, open(f"{ROOT}/{p}", "w"), ensure_ascii=False, indent=1)


def git(*a):
    subprocess.run(["git", "-C", ROOT, *a], check=True)


def commit(msg):
    git("add", "-A", "sent-log.json", "data")
    if subprocess.run(["git", "-C", ROOT, "diff", "--cached", "--quiet"]).returncode:
        git("commit", "-qm", msg)
        git("pull", "-q", "--rebase")
        git("push", "-q")


def render(q, who):
    key, svc_name, color = SVC[who]
    A = q["albums"]
    rows = "".join(f"""<tr><td style="padding:12px 12px 12px 0;border-top:1px solid #e3e0d8;width:96px;vertical-align:top">
<img src="{REPO_RAW}/{a['id']}.jpg" width="88" height="88" alt="" style="display:block;width:88px;height:88px;border-radius:6px"></td>
<td style="padding:12px 0;border-top:1px solid #e3e0d8;vertical-align:top">
<div style="font-size:12px;color:#777">{esc(a['released'])} · {esc(a['genre'])}</div>
<div style="font-size:16px;font-weight:700;margin:2px 0 4px">{esc(a['artist'])} 《{esc(a['title'])}》</div>
<div style="font-size:14px;line-height:1.55;color:#444">{esc(a['blurb'])}</div>
<a href="{esc(a[key])}" style="display:inline-block;margin-top:6px;font-size:14px;font-weight:700;color:{color};text-decoration:none">{svc_name}에서 듣기 · {esc(a['length'])}</a>
</td></tr>""" for a in A)
    P = lambda t: f'<p style="margin:0 0 16px;line-height:1.8;font-size:16px">{esc(t)}</p>'
    essays = "".join(
        f'<h2 style="font-size:19px;margin:30px 0 4px">{esc(e["heading"])}</h2>'
        f'<div style="font-size:13px;color:#777;margin-bottom:12px">{esc(next(a["artist"] + " 《" + a["title"] + "》" for a in A if a["id"] == e["id"]))}</div>'
        + "".join(P(t) for t in e["paras"]) for e in q["essays"])
    reads = "".join(f'<li style="margin:0 0 8px;line-height:1.5"><a href="{esc(r["url"])}" style="color:#1557b0;text-decoration:none">{esc(r["title"])}</a></li>' for r in q["readings"])
    total = q.get("total", "")
    body = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="margin:0;background:#f3f1eb;font-family:-apple-system,'Apple SD Gothic Neo','Noto Sans KR',Arial,sans-serif;color:#222">
<div style="max-width:680px;margin:0 auto;background:#fff;padding:28px 24px">
<div style="font-size:12px;letter-spacing:.06em;color:#777">대중음악 시간여행 · {q['year']}년 {q['partNo']}/{q['partTotal']}{(' · ' + esc(total)) if total else ''}</div>
<h1 style="font-size:25px;line-height:1.3;margin:8px 0 18px">{esc(q['title'])}</h1>
<div style="font-size:13px;font-weight:700;color:#555;margin-bottom:2px">오늘 들을 음반</div>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;border-bottom:1px solid #e3e0d8;margin-bottom:24px">{rows}</table>
{P(q['intro'])}
{essays}
<h2 style="font-size:17px;margin:30px 0 10px">더 읽을거리</h2><ul style="padding-left:18px;margin:0;font-size:14px">{reads}</ul>
<div style="margin:30px 0 4px;padding:16px;background:#f6f4ee;border-radius:8px;text-align:center">
<a href="{SITE}" style="font-size:15px;font-weight:700;color:#2f6f4f;text-decoration:none">흐름도에서 지금까지의 연결 보기 →</a></div>
</div></body></html>"""
    subj = f"대중음악 시간여행 · {q['year']}년 {q['partNo']}/{q['partTotal']} · {svc_name}"
    return subj, body


def send(to, subj, body):
    msg = MIMEText(body, "html", "utf-8")
    msg["Subject"], msg["To"] = subj, to
    msg["From"] = formataddr(("대중음악 시간여행", os.environ["SMTP_USER"]))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as s:
        pw = os.environ.get("SMTP_PASS", "").replace(" ", "").strip()
        print(f"SMTP 비밀번호 길이: {len(pw)} (16이어야 정상)")
        s.login(os.environ["SMTP_USER"], pw)
        s.send_message(msg)


def promote(q):
    """두 사람 모두 발송된 회차를 연표에 반영."""
    c = load("data/chronology.json")
    for ln in q.get("lanes", []):
        if ln not in c["lanes"]:
            c["lanes"].append(ln)
    ids = {n["id"]: n for n in c["nodes"]}
    for a in q["albums"]:
        n = ids.get(a["id"])
        if n is None:
            n = {"id": a["id"]}
            c["nodes"].append(n)
        n.update(year=q["year"], title=a["title"], artist=a["artist"], short=a.get("short", a["title"]),
                 lane=c["lanes"].index(a["lane"]), status="sent", part=q["part"],
                 spotify={"url": a["spotify"], "label": a["length"]}, apple={"url": a["apple"], "label": a["length"]})
    have = {(e["from"], e["to"]) for e in c["edges"]}
    c["edges"] += [e for e in q.get("edges", []) if (e["from"], e["to"]) not in have]
    c["updated"] = dt.datetime.now(KST).date().isoformat()
    save("data/chronology.json", c)


def main():
    test = os.environ.get("MODE") == "test"
    now = dt.datetime.now(KST)
    target = (now + dt.timedelta(minutes=30)).date()  # 23:30 이후 실행이면 '다음 날' 회차
    if not test:
        midnight = dt.datetime.combine(target, dt.time(0), KST)
        wait = (midnight - now).total_seconds()
        if 0 < wait <= 1800:
            print(f"자정까지 {wait:.0f}초 대기"); time.sleep(wait)
    log = load("sent-log.json", {})
    files = sorted(f for f in os.listdir(f"{ROOT}/queue") if f.endswith(".json"))
    due = [f for f in files if f[:10] <= target.isoformat()]
    pending = [f for f in due if not all(f"{load('queue/' + f)['part']}|{w}" in log for w in SVC)]
    future = [f for f in files if f[:10] > target.isoformat()]
    alert_to = os.environ.get("ALERT_TO") or os.environ["SMTP_USER"]

    if test:
        f = (pending or files)[0]
        q = load("queue/" + f)
        for w in SVC:
            subj, body = render(q, w)
            send(os.environ.get("TEST_TO") or alert_to, "[테스트] " + subj, body)
            print("test sent", w, f, len(body.encode()) // 1024, "KB")
        return

    if not pending:
        print("보낼 회차 없음")
        k = f"empty|{target}"
        if not any(f[:10] == target.isoformat() for f in files) and k not in log:
            send(alert_to, "[대중음악 시간여행] 오늘 보낼 원고 없음", f"<p>{target} 회차 원고가 큐에 없습니다.</p>")
            log[k] = now.isoformat(timespec="seconds"); save("sent-log.json", log); commit(k)
    else:
        f = pending[0]
        q = load("queue/" + f)
        for w in SVC:
            k = f"{q['part']}|{w}"
            if k in log:
                continue
            subj, body = render(q, w)
            send(os.environ["TO_GIHUN" if w == "gihun" else "TO_JUNGHUN"], subj, body)
            log[k] = dt.datetime.now(KST).isoformat(timespec="seconds")
            save("sent-log.json", log)
            commit(f"sent {k}")
            print("sent", k)
        promote(q)
        commit(f"chronology: {q['part']}")
        left = len(future) + len(pending) - 1
        if left < 3:  # 실제로 보낸 실행에서만 한 번 경고
            send(alert_to, f"[대중음악 시간여행] 남은 원고 {left}일치",
                 f"<p>예약된 원고가 {left}일치 남았습니다. 주간 집필 루틴이 돌았는지 확인하세요.</p>")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        try:
            send(os.environ.get("ALERT_TO") or os.environ["SMTP_USER"], "[대중음악 시간여행] 발송 오류", f"<pre>{html.escape(repr(e))}</pre>")
        finally:
            raise
