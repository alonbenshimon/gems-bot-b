import os, time, requests

BOT_TOKEN = os.environ.get("OKX_BOT_TOKEN", "").strip()

# Keywords that make an OKX announcement "relevant" for you
WATCH = {
    # tokens / your focus
    "avici", "tomi", "gems",

    # spot / listing lifecycle
    "spot", "spot trading",
    "listing", "list", "delist", "delisting",
    "deposit", "deposits", "withdraw", "withdrawal", "withdrawals",
    "suspend", "maintenance",

    # borrow / earn (relevant to you)
    "borrow", "loan", "flexible loan",
    "simple earn", "earn", "staking",
    "margin",  # keep (sometimes tied to borrow/earn changes)
}


def tg_api(method: str, data: dict):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    r = requests.post(url, data=data, timeout=25)
    return r.status_code, r.text


DERIVATIVE_TERMS = {
    # Derivatives keywords (NOT relevant unless spot/borrow is mentioned)
    "futures", "future", "perpetual", "perp", "swap", "funding", "um", "cm",
    "derivatives", "mark price", "index price", "position", "leverage",
}

SPOT_HINTS = {"spot", "spot trading"}
BORROW_HINTS = {"borrow", "loan", "flexible loan", "simple earn", "earn", "staking", "margin"}

def classify(text: str):
    t = text.lower()

    # If it's clearly futures/perpetual-only -> NOT relevant for you (spot + borrow focus)
    if ("perpetual" in t or "futures" in t) and ("spot" not in t) and ("borrow" not in t) and ("loan" not in t) and ("earn" not in t) and ("staking" not in t):
        return []

    hits = [w for w in WATCH if w in t]
    hits.sort()
    return hits

def main():
    if not BOT_TOKEN:
        return

    offset = 0
    while True:
        try:
            r = requests.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
                params={"timeout": 25, "offset": offset},
                timeout=35
            )
            data = r.json()
        except Exception:
            time.sleep(1)
            continue

        for upd in data.get("result", []):
            offset = max(offset, upd.get("update_id", 0) + 1)
            msg = upd.get("message") or upd.get("edited_message") or {}
            chat = msg.get("chat") or {}
            chat_id = chat.get("id")
            text = (msg.get("text") or msg.get("caption") or "").strip()
            if not chat_id or not text:
                continue

            cmd = text.lower().strip()
            if cmd in ("/start", "start"):
                tg_api("sendMessage", {"chat_id": chat_id, "text": "✅ Connected. Forward an OKX announcement and I will reply: RELEVANT / NOT RELEVANT."})
                continue
            if cmd in ("/ping", "ping"):
                tg_api("sendMessage", {"chat_id": chat_id, "text": "🏓 pong"})
                continue

            hits = classify(text)
            if hits:
                reply = "✅ RELEVANT\nMatched: " + ", ".join(hits[:20])
            else:
                reply = "❌ NOT RELEVANT"

            tg_api("sendMessage", {"chat_id": chat_id, "text": reply})

        time.sleep(0.3)

if __name__ == "__main__":
    main()