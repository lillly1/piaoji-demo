#!/usr/bin/env python3
"""Low-frequency proof-of-concept scraper for a public Ctrip mobile route page."""
from __future__ import annotations
import datetime as dt
import html
import json
import pathlib
import re
import urllib.request

URL = "https://m.ctrip.com/html5/flight/BJS-SHA-day-1.html"
OUT = pathlib.Path("data/ctrip-bjs-sha.json")
UA = "PiaojiDemoResearch/1.0 (+https://github.com/lillly1/piaoji-demo)"

def clean_page(raw: str) -> str:
    raw = re.sub(r"<(script|style)[^>]*>.*?</\\1>", " ", raw, flags=re.I | re.S)
    raw = re.sub(r"<[^>]+>", "\n", raw)
    text = html.unescape(raw).replace("\xa0", " ")
    return "\n".join(x.strip() for x in text.splitlines() if x.strip())

def parse(text: str) -> list[dict]:
    pattern = re.compile(
        r"(\\d{2}:\\d{2})\\s*([^\\n]{1,14})\\s*[⇀→]\\s*"
        r"(\\d{2}:\\d{2})\\s*([^\\n]{1,14})\\s*¥\\s*(\\d{2,5})"
    )
    rows, seen = [], set()
    for depart, dep_airport, arrive, arr_airport, price in pattern.findall(text):
        key = (depart, dep_airport, arrive, arr_airport, price)
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "depart": depart, "departAirport": dep_airport,
            "arrive": arrive, "arriveAirport": arr_airport,
            "price": int(price), "platform": "携程公开页"
        })
        if len(rows) >= 12:
            break
    return rows

def main() -> None:
    req = urllib.request.Request(URL, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        page = resp.read().decode("utf-8", errors="replace")
    text = clean_page(page)
    rows = parse(text)
    if not rows:
        raise RuntimeError("No public fare rows found; keep the last successful snapshot.")
    dates = re.findall(r"\\b(\\d{2}/\\d{2})\\b", text[:3000])
    payload = {
        "kind": "public-page-snapshot",
        "source": "携程移动端公开航线页",
        "sourceUrl": URL,
        "route": {"from": "北京", "to": "上海", "code": "BJS-SHA"},
        "displayDate": dates[0] if dates else None,
        "fetchedAt": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "notice": "公开页面低频采集实验；价格可能变化，不能作为可售报价。",
        "flights": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} rows to {OUT}")

if __name__ == "__main__":
    main()
