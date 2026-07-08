#!/bin/bash
# Passive, scope-gated, rate-limited recon arsenal.
# Usage: arsenal_passive.sh <scope-suffix> [checks] [rps]
#   echo host | arsenal_passive.sh example.com files,takeover 0.5
/home/altave/venv/bin/python3 /home/altave/.bughunter/tools/arsenal_passive.py \
  --scope "${1:?scope suffix required}" \
  --check "${2:-files,takeover}" \
  --rps "${3:-0.5}" \
  --ua "${ARSENAL_UA:-bughunter-passive/1.0}"
