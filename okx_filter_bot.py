from token_fix import extract_relevant_tokens
import os, time, requests

BASE = "https://www.gems.trade"
UA_HEADERS = {"User-Agent": "Mozilla/5.0"}

def get_markets():
    r = requests.get(f"{BASE}/api/v2/peatio/public/markets", headers=UA_HEADERS, timeout=20)
    r.raise_for_status()
    data = r.json()
    return [m["id"] for m in data if isinstance(m, dict) and "id" in m]

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

BOT_TOKEN = os.environ.get("OKX_BOT_TOKEN", "").strip()

def tg_api(method: str, data: dict):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    requests.post(url, data=data, timeout=25)

def classify(text: str):
    t = text.lower()

    if ("perpetual" in t or "futures" in t) and ("spot" not in t) and ("borrow" not in t):
        return None

    try:
        markets = get_markets()
    except Exception:
        return None

    relevant_tokens = extract_relevant_tokens(text, markets)
    if not relevant_tokens:
        return None

    types = []

    if "spot" in t or "pair" in t:
        types.append("Spot")

    if "delist" in t:
        types.append("Delist")

    if "borrow" in t or "borrowing" in t:
        types.append("Borrow")

    if "suspend" in t:
        types.append("Suspend")

    if "collateral" in t:
        types.append("Collateral")

    if "fee adjustment" in t or "group" in t:
        types.append("Fee Adjustment")

    if not types:
        types.append("Spot")

    TYPE_ORDER = ["Spot", "Borrow", "Delist", "Suspend", "Collateral", "Fee Adjustment"]
    ordered_types = [t for t in TYPE_ORDER if t in types]

    basket_map = build_basket_map()
    impacted_baskets = set()

    for token in relevant_tokens:
        base = token.lower()
        if base in basket_map:
            for b in basket_map[base]:
                impacted_baskets.add(b)

    return {
        "tokens": relevant_tokens,
        "types": ordered_types,
        "baskets": sorted(impacted_baskets)
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

            result = classify(text)

            if not result:
                reply = "❌ NOT RELEVANT"
            else:
                reply = "✅ RELEVANT\n\n"
                reply += f"Type: {', '.join(result['types'])}\n"
                reply += f"Token: {', '.join(result['tokens'])}"

                if result["baskets"]:
                    reply += "\n\nBasket Impact:\n"
                    for b in result["baskets"]:
                        reply += f"• {b}\n"

            tg_api("sendMessage", {"chat_id": chat_id, "text": reply})

        time.sleep(0.3)

if __name__ == "__main__":
    main()
