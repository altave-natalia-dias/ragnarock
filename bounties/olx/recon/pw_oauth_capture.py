#!/usr/bin/env python3
"""Capture OLX conta.olx.com.br OAuth/login flow via Playwright (system Chrome)."""
import sys, json, urllib.parse
from playwright.sync_api import sync_playwright

START = sys.argv[1] if len(sys.argv) > 1 else "https://conta.olx.com.br/identifique-se"
reqs = []

def on_request(req):
    reqs.append({"method": req.method, "url": req.url,
                 "rt": req.resource_type})

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True,
                          args=["--no-sandbox", "--disable-dev-shm-usage", "--lang=pt-BR"])
    ctx = b.new_context(locale="pt-BR",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")
    pg = ctx.new_page()
    pg.on("request", on_request)
    try:
        resp = pg.goto(START, wait_until="networkidle", timeout=45000)
        print("FINAL_URL:", pg.url)
        print("STATUS:", resp.status if resp else None)
        print("TITLE:", pg.title())
    except Exception as e:
        print("NAV_ERR:", repr(e)[:200])
        print("CUR_URL:", pg.url)
    # dump interesting requests
    print("\n=== auth/oauth-relevant requests ===")
    seen = set()
    for r in reqs:
        u = r["url"]
        if any(k in u.lower() for k in ["authorize", "oauth", "token", "login", "identifique",
                "client_id", "redirect_uri", "response_type", "code_challenge", "/auth", "openid",
                "conta.olx", "accounts-api", "auth-4ds", "apigw"]):
            key = u.split("?")[0]
            if u in seen: continue
            seen.add(u)
            print(f"[{r['method']}] {u[:300]}")
    # parse OAuth params from any authorize URL
    print("\n=== parsed OAuth params ===")
    for r in reqs:
        if "authorize" in r["url"].lower() or "response_type" in r["url"].lower() or "client_id" in r["url"].lower():
            q = urllib.parse.urlparse(r["url"]).query
            params = urllib.parse.parse_qs(q)
            if params:
                print(json.dumps({k: v[0] for k, v in params.items()}, indent=2, ensure_ascii=False))
                break
    ctx.close(); b.close()
