#!/usr/bin/env python3
"""Find OLX OAuth authorize entry by triggering login from main site + probing auth paths."""
import sys, json, urllib.parse
from playwright.sync_api import sync_playwright

reqs = []
def on_request(req): reqs.append((req.method, req.url))

PROBES = [
    "https://conta.olx.com.br/",
    "https://conta.olx.com.br/login",
    "https://conta.olx.com.br/oauth/authorize",
    "https://accounts-api.olx.com.br/",
]

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True,
                          args=["--no-sandbox", "--disable-dev-shm-usage", "--lang=pt-BR"])
    ctx = b.new_context(locale="pt-BR",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")
    pg = ctx.new_page()
    pg.on("request", on_request)

    # quick status probes
    print("=== path probes ===")
    for u in PROBES:
        try:
            r = pg.goto(u, wait_until="domcontentloaded", timeout=25000)
            print(f"{r.status if r else '?'}  {pg.url[:90]}  | {pg.title()[:50]}")
        except Exception as e:
            print(f"ERR {u} :: {repr(e)[:90]}")

    # trigger login from main site
    print("\n=== main site login trigger ===")
    reqs.clear()
    try:
        pg.goto("https://www.olx.com.br/", wait_until="networkidle", timeout=45000)
        print("home:", pg.url, "|", pg.title()[:40])
        # find login link
        found = None
        for sel in ['a[href*="conta.olx"]', 'a[href*="identifique"]', 'a[href*="login"]',
                    'text=Entrar', '[data-lurker-detail="login"]']:
            el = pg.query_selector(sel)
            if el:
                href = el.get_attribute("href")
                print("login element:", sel, "->", href)
                found = href or sel
                try:
                    el.click(timeout=5000)
                    pg.wait_for_load_state("networkidle", timeout=20000)
                    print("after click URL:", pg.url)
                except Exception as e:
                    print("click err:", repr(e)[:80])
                break
        if not found:
            print("no login element found via selectors")
    except Exception as e:
        print("home err:", repr(e)[:120])

    print("\n=== oauth/authorize requests seen ===")
    for m, u in reqs:
        if any(k in u.lower() for k in ["authorize","response_type","client_id","redirect_uri","oauth","openid","code_challenge"]):
            print(f"[{m}] {u[:320]}")
            q = urllib.parse.parse_qs(urllib.parse.urlparse(u).query)
            if "client_id" in q or "redirect_uri" in q:
                print("  PARAMS:", json.dumps({k:v[0] for k,v in q.items()}, ensure_ascii=False))
    ctx.close(); b.close()
