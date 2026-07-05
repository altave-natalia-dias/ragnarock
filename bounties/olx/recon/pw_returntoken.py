#!/usr/bin/env python3
import base64, json, urllib.parse
from playwright.sync_api import sync_playwright

def b64d(s):
    s += "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s)

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True,
        args=["--no-sandbox","--disable-dev-shm-usage","--lang=pt-BR"])
    ctx = b.new_context(locale="pt-BR",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")
    pg = ctx.new_page()
    # follow root -> /acesso
    r = pg.goto("https://conta.olx.com.br/", wait_until="domcontentloaded", timeout=30000)
    final = pg.url
    print("FINAL_URL:", final)
    q = urllib.parse.parse_qs(urllib.parse.urlparse(final).query)
    tok = q.get("returnToToken", [None])[0]
    if tok:
        open("returnToToken.jwt","w").write(tok)
        print("\nJWT:", tok[:80], "...")
        parts = tok.split(".")
        print("HEADER:", json.loads(b64d(parts[0])))
        print("PAYLOAD:", json.dumps(json.loads(b64d(parts[1])), indent=2, ensure_ascii=False))
        print("SIG(len):", len(parts[2]))
    else:
        print("no returnToToken; dumping all query params:", q)
    ctx.close(); b.close()
