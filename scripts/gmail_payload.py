"""오늘(KST) 보낼 메일을 Gmail 커넥터용 JSON으로 출력한다. 표지 이미지는 커넥터가 외부 이미지를 지우므로 뺀다.
사용: python3 scripts/gmail_payload.py [YYYY-MM-DD]
출력: {"date":..., "part":..., "pending":[{"who","key","to","subject","htmlBody"}...]}  (이미 보낸/예약된 수신자는 제외)"""
import datetime as dt, json, os, re, sys
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, f"{ROOT}/scripts")
import send  # noqa: E402

TO = {"gihun": "kikisnu21@snu.ac.kr", "junghun": "junghunjulian@gmail.com"}
date = sys.argv[1] if len(sys.argv) > 1 else dt.datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat()
f = f"{ROOT}/queue/{date}.json"
if not os.path.exists(f):
    last = sorted(os.listdir(f"{ROOT}/queue"))[-1][:10]
    print(json.dumps({"date": date, "none": True, "lastQueueDate": last}, ensure_ascii=False))
    sys.exit(0)
q = json.load(open(f))
log = json.load(open(f"{ROOT}/sent-log.json"))
out = []
for w in ("gihun", "junghun"):
    key = f"{q['part']}|{w}"
    if key in log:
        continue
    subj, body = send.render(q, w)
    body = re.sub(r'<td style="padding:12px 12px 12px 0;[^"]*">\s*<img [^>]*></td>', "", body)  # 표지 칸 제거
    out.append({"who": w, "key": key, "to": TO[w], "subject": subj, "htmlBody": body})
print(json.dumps({"date": date, "part": q["part"], "pending": out}, ensure_ascii=False))
