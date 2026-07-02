#!/bin/bash
# Probe throttled: 1 request a cada 1.2s (~50 req/min, margem abaixo do limite de 60/min da política)
IN=in_scope_hosts.txt
OUT=httpx_probe_results.tsv
echo -e "host\tip\tscheme\tstatus\tserver\ttitle\tcontent_length" > "$OUT"
while IFS=$'\t' read -r host ips; do
  ip=$(echo "$ips" | cut -d, -f1)
  for scheme in https http; do
    resp=$(curl -sk -o /tmp/body.html -D /tmp/headers.txt -m 8 --max-redirs 2 -w "%{http_code}" "$scheme://$host/" 2>/dev/null)
    status="${resp:-000}"
    if [ "$status" != "000" ]; then
      server=$(grep -i '^server:' /tmp/headers.txt | head -1 | cut -d: -f2- | tr -d '\r' | xargs)
      title=$(grep -ioP '(?<=<title>).*?(?=</title>)' /tmp/body.html 2>/dev/null | head -1)
      clen=$(wc -c < /tmp/body.html)
      echo -e "${host}\t${ip}\t${scheme}\t${status}\t${server}\t${title}\t${clen}" >> "$OUT"
      break
    fi
  done
  sleep 1.2
done < "$IN"
