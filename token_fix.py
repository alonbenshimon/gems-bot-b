import re

def extract_relevant_tokens(text, markets):
    t = text.lower()
    bases = set()

    for m in markets:
        m = m.lower()
        if m.endswith("usdt"):
            bases.add(m[:-4])
        elif m.endswith("btc"):
            bases.add(m[:-3])

    found = []
    for base in bases:
        pattern = r'\b' + re.escape(base) + r'\b'
        if re.search(pattern, t):
            found.append(base.upper())

    return sorted(found)
