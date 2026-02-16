import os
import time
import requests
from token_fix import extract_relevant_tokens

BOT_TOKEN = os.environ.get("OKX_BOT_TOKEN", "").strip()

BASE = "https://www.gems.trade"
UA_HEADERS = {"User-Agent": "Mozilla/5.0"}

OKX_CATEGORY_URL = "https://www.okx.com/help/category/announcements"


def get_markets():
    r = requests.get(f"{BASE}/api/v2/peatio/public/markets", headers=UA_HEADERS, timeout=20)
    r.raise_for_status()
    data = r.json()
    return [m["id"] for m in data if isinstance(m, dict) and "id" in m]


def tg_send(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=20)


def fetch_latest_okx_links():
    try:
        r = requests.get(OKX_CATEGORY_URL, headers=UA_HEADERS, timeout=20)
        html = r.text
    except Exception:
        return []

    links = []
    for part in html.split("/help/okx-to-")[1:]:
        slug = part.split('"')[0]
        full = f"https://www.okx.com/help/okx-to-{slug}"
        links.append(full)

    return list(dict.fromkeys(links))[:5]


def fetch_article_title_and_text(url):
    try:
        r = requests.get(url, headers=UA_HEADERS, timeout=20)
        html = r.text
    except Exception:
        return None, None

    title = None
    if "<h1" in html:
        try:
            title = html.split("<h1")[1].split(">")[1].split("</h1>")[0]
        except Exception:
            title = None

    return title, html


def classify(text, markets):
    relevant_tokens = extract_relevant_tokens(text, markets)
    if not relevant_tokens:
        return None

    t = text.lower()
    types = []

    if "spot" in t or "pair" in t:
        types.append("Spot")
    if "delist" in t:
        types.append("Delist")
    if "borrow" in t:
        types.append("Borrow")
    if "fee adjustment" in t or "group" in t:
        types.append("Fee Adjustment")

    if not types:
        types.append("Spot")

    return {
        "tokens": relevant_tokens,
        "types": types
    }


def main():
    print("OKX AUTO BOT STARTED")

    if not BOT_TOKEN:
        print("NO BOT TOKEN")
        return

    markets = get_markets()
    last_seen = set(fetch_latest_okx_links())

    # >>> תכניס כאן את ה-chat_id שלך
    CHAT_ID = 7652982274

    while True:
        links = fetch_latest_okx_links()

        for url in links:
            if url in last_seen:
                continue

            title, full_text = fetch_article_title_and_text(url)
            if not title:
                continue

            result = classify(title + " " + full_text, markets)

            if result:
                reply = "✅ RELEVANT\n\n"
                reply += f"Type: {', '.join(result['types'])}\n"
                reply += f"Token: {', '.join(result['tokens'])}\n\n"
                reply += f"Source:\n{url}"
                tg_send(CHAT_ID, reply)

            last_seen.add(url)

        time.sleep(120)


if __name__ == "__main__":
    main()
