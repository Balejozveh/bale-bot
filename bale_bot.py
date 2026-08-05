import json, urllib.request, urllib.error, base64, time, os, logging

log = logging.getLogger("bale-bot")
logging.basicConfig(level=logging.INFO)

# ===== Config =====
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
CARD_NUMBER = os.environ.get("CARD_NUMBER", "6104 3371 7217 0951")
CARD_HOLDER = os.environ.get("CARD_HOLDER", "جواد شوقیان")
GH_TOKEN = os.environ.get("GH_TOKEN", "")
GH_REPO = os.environ.get("GH_REPO", "jozvehtelegram/receipts")
CF_TOKEN = os.environ.get("CF_TOKEN", "")
CF_ACCOUNT = os.environ.get("CF_ACCOUNT", "")
CF_DB = os.environ.get("CF_DB", "")

API = f"https://tapi.bale.ai/bot{BOT_TOKEN}"

COURSES = {
    "hesaban": {"name": "جزوه حسابان", "amount": 380000, "deadline": "جمعه ۱۶ مرداد — ساعت ۱۸:۰۰"},
    "hendese": {"name": "جزوه هندسه",  "amount": 280000, "deadline": "شنبه ۱۷ مرداد — ساعت ۲۱:۰۰"},
    "shimi":   {"name": "جزوه شیمی",  "amount": 750000, "deadline": "جمعه ۱۶ مرداد — ساعت ۲۱:۰۰"},
}

# ===== Helpers =====
def api_call(method, payload):
    url = f"{API}/{method}"
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        log.error("API %s failed: %s", method, e)
        return {"ok": False}

def send_message(chat_id, text, kb=None, parse_mode="HTML"):
    p = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if kb: p["reply_markup"] = kb
    return api_call("sendMessage", p)

def send_photo(chat_id, file_id, caption="", kb=None, parse_mode="HTML"):
    p = {"chat_id": chat_id, "photo": file_id, "caption": caption, "parse_mode": parse_mode}
    if kb: p["reply_markup"] = kb
    return api_call("sendPhoto", p)

def edit_message(chat_id, message_id, text, kb=None):
    p = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if kb: p["reply_markup"] = kb
    return api_call("editMessageText", p)

def edit_caption(chat_id, message_id, caption, kb=None):
    p = {"chat_id": chat_id, "message_id": message_id, "caption": caption}
    if kb: p["reply_markup"] = kb
    return api_call("editMessageCaption", p)

def answer_cb(cb_id, text=None):
    p = {"callback_query_id": cb_id}
    if text: p["text"] = text
    return api_call("answerCallbackQuery", p)

def persian_now():
    from datetime import datetime, timedelta
    now = datetime.utcnow() + timedelta(hours=3, minutes=30)
    jy = 1405; jm = 5; jd = now.day  # simplified: Mordad month offset
    days = (now - datetime(2026, 7, 23)).days  # 1 Mordad 1405 = Jul 23 2026
    months = [31,31,31,31,31,31,30,30,30,30,30,29]
    jd2 = days + 1; jm2 = 5; jy2 = 1405
    if jd2 > 31: jd2 -= 31; jm2 = 6
    # fine approximation for Mordad
    return f"{jd2} مرداد ۱۴۰۵", f"{now.hour:02d}:{now.minute:02d}"

# ===== Upload receipt to GitHub =====
def upload_to_github(data, filename):
    if not GH_TOKEN: return None
    try:
        content = base64.b64encode(data).decode()
        payload = json.dumps({"message": f"upload {filename}", "content": content, "branch": "main"}).encode()
        url = f"https://api.github.com/repos/{GH_REPO}/contents/receipts/{filename}"
        req = urllib.request.Request(url, data=payload, headers={
            "Authorization": f"Bearer {GH_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"}, method="PUT")
        with urllib.request.urlopen(req, timeout=25) as resp:
            d = json.loads(resp.read())
            raw = d.get("content", {}).get("download_url") or ""
            if "github.com/" in raw:
                raw = raw.replace("github.com/", "raw.githubusercontent.com/").split("?token=")[0]
            return raw or None
    except Exception as e:
        log.error("GH upload failed: %s", e)
        return None

def get_file_path(file_id):
    r = api_call("getFile", {"file_id": file_id})
    if r.get("ok"):
        return r["result"].get("file_path")
    return None

def download_file(file_path):
    try:
        url = f"https://tapi.bale.ai/file/bot{BOT_TOKEN}/{file_path}"
        with urllib.request.urlopen(url, timeout=30) as resp:
            return resp.read()
    except Exception as e:
        log.error("Download failed: %s", e)
        return None

# ===== D1 =====
def save_to_d1(name, course_name, amount, date, time, bale_id, image_url=None):
    safe_name = name.replace("'", "''")
    img = f"'{image_url.replace(chr(39), chr(39)+chr(39))}'" if image_url else "NULL"
    bale = f"'{str(bale_id).replace(chr(39), chr(39)+chr(39))}'" if bale_id is not None else "NULL"
    sql = ("INSERT INTO payments (name, amount, date, time, image_url, course, tg_id, bale_id) "
           f"VALUES ('{safe_name}', {amount}, '{date}', '{time}', {img}, "
           f"'{course_name.replace(chr(39), chr(39)+chr(39))}', NULL, {bale})")
    payload = json.dumps({"sql": sql}).encode()
    url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/d1/database/{CF_DB}/raw"
    req = urllib.request.Request(url, data=payload, headers={
        "Authorization": f"Bearer {CF_TOKEN}",
        "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            d = json.loads(resp.read())
            return bool(d.get("success"))
    except Exception as e:
        log.error("D1 save failed: %s", e)
        return False

# ===== State =====
user_state = {}  # chat_id -> dict(name, course_key, ...)

def save_user(chat_id, platform="bale"):
    """Record user chat_id for future broadcasts (idempotent)."""
    try:
        check_sql = f"SELECT COUNT(*) FROM users WHERE chat_id='{chat_id}' AND platform='{platform}'"
        payload = json.dumps({"sql": check_sql}).encode()
        url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/d1/database/{CF_DB}/raw"
        req = urllib.request.Request(url, data=payload, headers={
            "Authorization": f"Bearer {CF_TOKEN}",
            "Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            count = data["result"][0]["results"]["rows"][0][0]
        if count > 0:
            return True
        sql = f"INSERT INTO users (chat_id, platform) VALUES ('{chat_id}', '{platform}')"
        payload = json.dumps({"sql": sql}).encode()
        req = urllib.request.Request(url, data=payload, headers={
            "Authorization": f"Bearer {CF_TOKEN}",
            "Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return bool(data.get("success"))
    except Exception as e:
        log.error("save_user failed: %s", e)
        return False

# ===== Handlers =====
def handle_start(chat_id):
    save_user(chat_id, "bale")
    kb = {"inline_keyboard": [
        [{"text": "🌐 ثبت سفارش در وب (سریع‌تر)", "url": "https://ble.ir/jozveh_r1_bot?startapp"}],
        [{"text": "📚 جزوه حسابان (380000 تومان)", "callback_data": "course_hesaban"}],
        [{"text": "📚 جزوه هندسه (280000 تومان)", "callback_data": "course_hendese"}],
        [{"text": "📚 جزوه شیمی (750000 تومان)", "callback_data": "course_shimi"}]
    ]}
    deadline_lines = "\n".join(f"🔸 {c['name']}: تا {c['deadline']}" for c in COURSES.values())
    send_message(chat_id,
        "سلام! 👋\nبه بات جمع‌آوری واریزی خوش اومدی.\nمی‌تونی از دکمه «ثبت سفارش در وب» سریع‌تر سفارش بدی، یا از همین‌جا ادامه بدی:\n\n"
        f"⏳ مهلت واریز:\n{deadline_lines}\n\n⚠️ بعد از مهلت تعیین‌شده، امکان واریز وجود نداره!",
        kb)

def handle_course_cb(chat_id, msg_id, cb_id, key, user_id):
    if key not in COURSES:
        send_message(chat_id, "⚠️ درس نامعتبر! دوباره /start بزن.")
        return
    course = COURSES[key]
    user_state[chat_id] = {"course": key, "course_name": course["name"], "amount": course["amount"], "stage": "name"}
    edit_message(chat_id, msg_id,
        f"📚 {course['name']} انتخاب شد!\n\n✍️ حالا نام و نام خانوادگی خودت رو به صورت کامل بفرست.\n(مثلاً: علی کلماتی)")
    answer_cb(cb_id)

def handle_name(chat_id, text):
    st = user_state.get(chat_id)
    if not st or st.get("stage") != "name":
        send_message(chat_id, "⚠️ اول /start بزن.")
        return
    if len(text.split()) < 2:
        send_message(chat_id, "⚠️ لطفاً نام و نام خانوادگی کامل رو بفرست.\nمثلاً: علی کلماتی")
        return
    st["name"] = text.strip()
    st["stage"] = "receipt"
    send_message(chat_id,
        f"👤 {st['name']} عزیز، ثبت شد!\n\n📚 درس: {st['course_name']}\n"
        f"💳 برای پرداخت مبلغ {st['amount']:,} تومان، به کارت زیر واریز کن:\n\n"
        f"💳 {CARD_NUMBER}\nبه نام: {CARD_HOLDER}\n\n"
        f"📸 حالا عکس رسید واریزی رو بفرست.\n\n"
        f"⚠️ توجه: بهتره عکس رسید رو بلافاصله بعد از واریز بفرستی تا زمان دقیق واریز ثبت بشه!")

def handle_receipt(chat_id, file_id):
    st = user_state.get(chat_id)
    if not st or st.get("stage") != "receipt":
        send_message(chat_id, "⚠️ اول /start بزن.")
        return
    date_str, time_str = persian_now()
    image_url = None
    fp = get_file_path(file_id)
    if fp:
        data = download_file(fp)
        if data:
            image_url = upload_to_github(data, f"receipt_{int(time.time())}.jpg")
    caption = (f"🆕 واریزی جدید (از بات بله)\n\n📚 درس: {st['course_name']}\n"
        f"👤 نام: {st['name']}\n💵 مبلغ: {st['amount']:,} تومان\n📅 تاریخ: {date_str}\n"
        f"⏰ ساعت: {time_str}\n🆔 بله: {chat_id}"
        + (f"\n🖼️ لینک رسید: {image_url}" if image_url else "\n⚠️ آپلود رسید ناموفق بود")
        + "\n\n🔐 برای تأیید/رد از پنل ادمین اقدام کن: variyabi-api.edis-edfamily.workers.dev/admin")
    # فقط خبر — بدون دکمه تأیید/رد
    resp = send_photo(ADMIN_ID, file_id, caption)
    # ثبت مستقیم در D1 با وضعیت pending
    try:
        save_to_d1(st["name"], st["course_name"], st["amount"], date_str, time_str, None, image_url)
    except Exception as e:
        log.error("D1 save failed: %s", e)
    send_message(chat_id, "✅ رسید دریافت شد!\n\n⏳ در حال بررسی توسط ادمین...\nبعد از تایید، پیام نهایی بهت می‌رسه. صبر کن 🙏")
    user_state.pop(chat_id, None)

def handle_admin_cb(chat_id, msg_id, cb_id, data, from_id):
    if from_id != ADMIN_ID:
        answer_cb(cb_id, "❌ شما ادمین نیستید!")
        return
    answer_cb(cb_id)

    # ── new webapp buttons: wa_approve:<platform>:<payment_id> / wa_reject:<platform>:<payment_id> ──
    if data.startswith(("wa_approve:", "wa_reject:")):
        parts = data.split(":")
        action = parts[0]
        pay_id = parts[2] if len(parts) > 2 else parts[1]  # wa_approve:telegram:47 → 47
        status = "approved" if action == "wa_approve" else "cancelled"
        try:
            payload = json.dumps({"id": int(pay_id), "status": status}).encode()
            req = urllib.request.Request(
                "https://variyabi-api.edis-edfamily.workers.dev/api/webapp/status",
                data=payload,
                headers={"Content-Type": "application/json", "User-Agent": "variyabi-bale"},
                method="POST")
            with urllib.request.urlopen(req, timeout=25) as resp:
                d = json.loads(resp.read())
            if d.get("success"):
                edit_caption(chat_id, msg_id,
                    ("" ) + f"🆕 واریزی جدید\n\n{'✅ تایید شد!' if status=='approved' else '❌ رد شد'}")
            else:
                answer_cb(cb_id, "⚠️ خطا در ثبت!")
        except Exception as e:
            log.error("wa status failed: %s", e)
            answer_cb(cb_id, "⚠️ خطا در ارتباط")
        return

    action, target = data.split(":")
    m = api_call("getChat", {"chat_id": target}) if False else None
    # Parse caption from stored message: we need caption — fetch from our memory
    # Simplest: store last pending payment globally
    pending = PENDING.get(msg_id)
    if not pending:
        edit_caption(chat_id, msg_id, "⚠️ اطلاعات این پیام دیگه در دسترس نیست.")
        return
    name, course_name, amount, image_url = pending["name"], pending["course"], pending["amount"], pending["image"]
    if action == "approve":
        date_str, time_str = persian_now()
        ok = save_to_d1(name, course_name, amount, date_str, time_str, int(target), image_url)
        status = "✅ تایید شد!" if ok else "❌ خطا در ذخیره!"
        edit_caption(chat_id, msg_id, f"🆕 واریزی جدید منتظر تایید\n📚 درس: {course_name}\n👤 نام: {name}\n💵 مبلغ: {amount:,} تومان\n\n{status}")
        if ok:
            send_message(int(target), f"✅ واریزی شما تایید شد!\n\n📚 درس: {course_name}\n👤 {name}\n💵 مبلغ: {amount:,} تومان\n\n🙏 ممنون، همه‌چی ثبت شد.")
    elif action == "reject":
        edit_caption(chat_id, msg_id, f"🆕 واریزی جدید منتظر تایید\n📚 درس: {course_name}\n👤 نام: {name}\n\n❌ رد شد")
        send_message(int(target), "❌ متأسفانه واریزی شما تایید نشد.\nلطفاً دوباره /start بزن و با دقت اطلاعات رو بفرست.")
    PENDING.pop(msg_id, None)

PENDING = {}  # message_id -> payment info (set when receipt sent to admin)

# ===== Main loop =====
def main():
    offset = 0
    log.info("Bale bot polling...")
    while True:
        r = api_call("getUpdates", {"offset": offset, "timeout": 30})
        if not r.get("ok"):
            time.sleep(3); continue
        for u in r["result"]:
            offset = u["update_id"] + 1
            if "callback_query" in u:
                cq = u["callback_query"]
                msg = cq.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                msg_id = msg.get("message_id")
                data = cq.get("data", "")
                from_id = cq.get("from", {}).get("id")
                if not chat_id: continue
                # Save user id on ANY interaction (not just /start)
                save_user(from_id or chat_id, "bale")
                if data.startswith("course_"):
                    handle_course_cb(chat_id, msg_id, cq["id"], data[7:], from_id)
                elif data.startswith(("approve:", "reject:", "wa_approve:", "wa_reject:")):
                    handle_admin_cb(chat_id, msg_id, cq["id"], data, from_id)
            elif "message" in u:
                m = u["message"]
                chat_id = m.get("chat", {}).get("id")
                text = m.get("text", "")
                # Save user id on ANY message
                save_user(chat_id, "bale")
                if text == "/start":
                    handle_start(chat_id)
                elif m.get("photo"):
                    file_id = m["photo"][-1]["file_id"]
                    handle_receipt(chat_id, file_id)
                elif text:
                    handle_name(chat_id, text)

if __name__ == "__main__":
    main()
