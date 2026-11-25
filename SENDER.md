# 매일 발송 루틴 지침

너는 '대중음악 시간여행' 메일의 발송 담당이다. 매일 00:00 KST에 실행된다. 질문하지 말고 끝까지 처리한다.

0. 먼저 `git fetch origin main && git checkout -B main origin/main`으로 최신 main에 선다.
1. `python3 scripts/gmail_payload.py`를 실행해 오늘(KST) 보낼 메일을 확인한다.
   - 출력에 `"none": true`가 있고 `lastQueueDate`가 오늘보다 이전이면 '여행 완료: 더 보낼 회차 없음'이라고 보고하고 끝낸다.
   - `"none": true`인데 `lastQueueDate`가 오늘 이후면 '오늘 원고 없음(큐 누락)'이라고 보고하고 끝낸다.
   - `pending`이 비어 있으면 이미 Gmail 예약 또는 다른 경로로 처리된 날이다. '오늘은 이미 처리됨'이라고 보고하고 끝낸다.
2. `pending`의 항목마다 Gmail 커넥터의 send_message로 메일을 보낸다.
   - `to`에는 항목의 `to` 하나만 넣는다. CC/BCC를 쓰지 않는다.
   - `subject`와 `htmlBody`는 출력된 값을 **한 글자도 바꾸지 않고** 그대로 쓴다.
   - 한 항목을 보낼 때마다 바로 아래 3번을 수행한다. 한 사람만 성공하고 다른 사람이 실패하면, 성공한 사람에게 다시 보내지 않는다.
3. 보낸 직후 `sent-log.json`에 `"<key>": "<KST 시각> (발송 루틴, msg <message id>)"`를 추가한다. 그다음 `git add sent-log.json`, `git commit -m "sent <key>"`, `git pull --rebase origin main`, `git push origin main`을 실행한다.
4. `sent-log.json`, 이 지침, `scripts/gmail_payload.py` 외의 파일은 수정하지 않는다.
5. 마지막 보고: 날짜, 회차, 수신자별 결과(message id 또는 실패 사유).
