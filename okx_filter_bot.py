import os, time, requests

BASE = "https://www.gems.trade"
UA_HEADERS = {"User-Agent": "Mozilla/5.0"}
def get_markets():
    r = requests.get(f"{BASE}/api/v2/peatio/public/markets", headers=UA_HEADERS, timeout=20)
    r.raise_for_status()
    data = r.json()
    return [m["id"] for m in data if isinstance(m, dict) and "id" in m]
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

    # 1. סינון futures בלבד
    if ("perpetual" in t or "futures" in t) and ("spot" not in t) and ("borrow" not in t):
        return None

    # 2. שליפת markets
    try:
        markets = get_markets()
    except Exception:
        return None

    bases = set()
    for m in markets:
        m = m.lower()
        if m.endswith("usdt"):
            bases.add(m[:-4])
        elif m.endswith("btc"):
            bases.add(m[:-3])

    relevant_tokens = sorted([b.upper() for b in bases if b in t])

    if not relevant_tokens:
        return None

    # 3. זיהוי Type
    types = []

    if "spot" in t or "pair" in t:
        types.append("Spot")

    if "delist" in t:
        types.append("Delist")

    if "borrow" in t or "borrowing" in t:
        types.append("Borrow")

    if "suspend" in t or "suspended" in t:
        types.append("Suspend")

    if "collateral" in t:
        types.append("Collateral")

    if "fee adjustment" in t or "group" in t:
        types.append("Fee Adjustment")

    # אם אין סוג אבל יש מטבע רלוונטי — נחשב כ-Spot
    if not types:
        types.append("Spot")

    return {
        "tokens": relevant_tokens,
        "types": sorted(set(types))
    }
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
            if cmd in ("/ping", "ping"):
                tg_api("sendMessage", {"chat_id": chat_id, "text": "🏓 pong"})
            result = classify(text)

            if not result:
                reply = "❌ NOT RELEVANT"
            else:
                tokens = ", ".join(result["tokens"])
                types = ", ".join(result["types"])

                reply = "✅ RELEVANT\n\n"
                reply += f"Type: {types}\n"
                reply += f"Token: {tokens}"

            tg_api("sendMessage", {"chat_id": chat_id, "text": reply})
        time.sleep(0.3)
if __name__ == "__main__":
    main()

def get_baskets():
    r = requests.get(f"{BASE}/api/v2/peatio/public/baskets", headers=UA_HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()

def build_basket_map():
    baskets = get_baskets()
    token_map = {}
    for b in baskets:
        name = b.get("name")
        for m in b.get("market_list", []):
            market = m.get("market", "").lower()
            if market.endswith("usdt"):
                base = market[:-4]
            elif market.endswith("btc"):
                base = market[:-3]
            else:
                continue
            token_map.setdefault(base, []).append(name)
    return token_map
