# -*- coding: utf-8 -*-
"""Letterboxd friends -> Telegram channel (spoilers hidden, poster, friend tag)."""
import os, re, json, html, time, urllib.request, urllib.error
import xml.etree.ElementTree as ET

# ============ فقط این بخش رو ویرایش کن ============
# "یوزرنیم در لترباکس": "اسمی که می‌خوای به‌صورت تگ بیاد"
FRIENDS = {
    "rezali": "Rezali",
    "Bahaar_": "Bahare shirazi",
    "SalaRah": "Salar Rahimi",
    "mahmoudreza": "Mahmood Taghavi",
    "nimahamed88": "nima_franch",
    "AlirezaDehghan": "Alireza Dehghon",
    "Aliireza": "Alireza Dehghon2",
    "SalaRah": "Salar Rahimi",
    "mahmoudreza": "mahmoudreza",
    "raybo": "Raybo",
    "elhumanl": "Elham",
    "nimahamed88": "Nima Hamed",
    "nagualwitch": "NagualWitch",
    "chekkechekke": "‮‬chekkechekke",
    "royabr": "Roya Br",
    "m_yousof_r": "Yousof Rafizadeh",
    "cloudmooni": "Cloudmooni",
    "sarahetesami": "Sarah Etesami",
    "masih_norouzi": "Masih_Norouzi",
    "naiad_m": "Niloofar",
    "forrelain": "Sam",
    "taranehc": "Taraneh",
    "honeybahram": "HoNeY BhR",
    "frimarz": "Farima",
    "ichlucifer": "HodA",
    "armanvikiliz": "Arman",
    "nedaazizi": "Neda Azizi",
    "ja3mine": ". 𝙹 𝙰 𝚂 𝙼 𝙸 𝙽 𝙴 .",
    "faellla": "Faella",
    "negarsuffi": "Negar Suffi",
    "shirin_javdani": "shirin Javdani",
    "razi1995": "razi1995",
    "nimahd": "Nima hadad",
    "eli_zizi": "elham azizi",
    "zenith24": "Zeinab",
    "parisa94": "parisa94",
    "moakhi": "Mohammad akhlaghi",
    "erf514": "Erfan Nazari",
    "sina18ayati": "sina18ayati",
    "negarfard": "Negar Fard",
    "hpez": "Hassan Pezeshk",
    "kimiasadr": "Kimia Sadreddini",
    "mortezaghasemi": "MortezaGhasemi",
    # "another_user": "سارا",
}
# ==================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL = os.environ.get("CHANNEL_ID", "")
TEST_MODE = os.environ.get("TEST_MODE", "").strip().lower() in ("true", "1", "yes")
STATE_FILE = "state.json"
UA = "Mozilla/5.0 (compatible; FriendsFeedBot/1.0)"
MAX_REVIEW = 600      # حداکثر طول نقد در پیام
MAX_NEW_PER_RUN = 10  # برای جلوگیری از سیل پیام


def local(tag):
    return tag.rsplit("}", 1)[-1]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def parse_items(xml_bytes):
    root = ET.fromstring(xml_bytes)
    items = []
    for it in root.iter("item"):
        d = {}
        for ch in it:
            d[local(ch.tag)] = (ch.text or "").strip()
        items.append(d)
    return items


def stars(rating):
    try:
        r = float(rating)
    except (TypeError, ValueError):
        return ""
    full = int(r)
    return "★" * full + ("½" if r - full >= 0.5 else "")


SPOILER_RE = re.compile(r"(may )?contains? spoilers?", re.I)


def clean_description(desc):
    """returns (poster_url, review_text, spoiler_flag)"""
    spoiler = bool(SPOILER_RE.search(desc))
    m = re.search(r'<img[^>]+src="([^"]+)"', desc)
    poster = m.group(1) if m else None
    t = re.sub(r"<img[^>]*>", "", desc)
    t = re.sub(r"</p>|<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t)
    lines = []
    for ln in t.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        if SPOILER_RE.search(ln) and len(ln) < 60:
            continue
        if re.match(r"^Watched on .*\.$", ln):
            continue
        lines.append(ln)
    text = "\n".join(lines)
    if len(text) > MAX_REVIEW:
        text = text[:MAX_REVIEW].rsplit(" ", 1)[0] + "…"
    return poster, text, spoiler


def tag_for(name):
    return "#" + re.sub(r"[^\w]", "_", name, flags=re.U)


def build_message(item, friend_name):
    e = html.escape
    title = item.get("filmTitle", "")
    year = item.get("filmYear", "")
    link = item.get("link", "")
    m = re.search(r"/film/([^/]+)/", link)
    film_url = f"https://letterboxd.com/film/{m.group(1)}/" if m else link
    poster, review, spoiler = clean_description(item.get("description", ""))
    if SPOILER_RE.search(item.get("title", "")):
        spoiler = True

    lines = [f'🎬 <a href="{e(film_url)}">{e(title)}{" (" + e(year) + ")" if year else ""}</a>']
    st = stars(item.get("memberRating"))
    rating_line = ""
    if st:
        rating_line = f"{st}  ({item['memberRating']}/5)"
    elif not review:
        rating_line = "👀 دیده شد"
    if item.get("rewatch", "").lower() == "yes":
        rating_line = (rating_line + "  🔁 دوباره دیده").strip()
    if rating_line:
        lines.append(rating_line)
    lines.append(f"👤 {tag_for(friend_name)}")

    if review:
        lines.append("")
        if spoiler:
            lines.append("⚠️ این نظر اسپویل داره (برای دیدن لمس کن):")
            lines.append(f"<tg-spoiler>{e(review)}</tg-spoiler>")
        else:
            lines.append(e(review))
        lines.append("")
        lines.append(f'🔗 <a href="{e(link)}">نظر در لترباکس</a>')
    return "\n".join(lines), poster


def tg(method, payload):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as ex:
        body = ex.read().decode("utf-8", "ignore")
        if ex.code == 429:
            try:
                wait = json.loads(body)["parameters"]["retry_after"]
            except Exception:
                wait = 10
            time.sleep(wait + 1)
            return tg(method, payload)
        print(f"Telegram error {ex.code}: {body}")
        return None


def send(item, friend_name):
    text, poster = build_message(item, friend_name)
    if poster:
        r = tg("sendPhoto", {"chat_id": CHANNEL, "photo": poster, "caption": text, "parse_mode": "HTML"})
        if r and r.get("ok"):
            return True
    r = tg("sendMessage", {"chat_id": CHANNEL, "text": text, "parse_mode": "HTML",
                           "disable_web_page_preview": True})
    return bool(r and r.get("ok"))


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"seen": {}}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)


def main():
    state = load_state()
    seen_all = state.setdefault("seen", {})
    for username, friend_name in FRIENDS.items():
        url = f"https://letterboxd.com/{username}/rss/"
        try:
            items = parse_items(fetch(url))
        except Exception as ex:
            print(f"[{username}] could not read feed: {ex}")
            continue
        items = [i for i in items if i.get("filmTitle")]  # لیست‌ها حذف میشن
        guids = [i.get("guid") or i.get("link") for i in items]

        if TEST_MODE:
            if items:
                print(f"[{username}] test: sending latest item")
                send(items[0], friend_name)
            continue

        if username not in seen_all:  # اولین اجرا: فقط ثبت کن، چیزی نفرست
            seen_all[username] = guids[:200]
            print(f"[{username}] first run: {len(guids)} items marked as seen")
            continue

        seen = set(seen_all[username])
        new = [(g, i) for g, i in zip(guids, items) if g not in seen]
        new = list(reversed(new))  # قدیمی‌ترین اول
        for g, i in new[-MAX_NEW_PER_RUN:]:
            if send(i, friend_name):
                time.sleep(3)
        seen_all[username] = (guids + seen_all[username])[:200]
        print(f"[{username}] new items: {len(new)}")
    save_state(state)


if __name__ == "__main__":
    if not BOT_TOKEN or not CHANNEL:
        raise SystemExit("BOT_TOKEN or CHANNEL_ID is missing")
    main()
