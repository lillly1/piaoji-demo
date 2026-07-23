from __future__ import annotations

import asyncio
import datetime as dt
import html as html_lib
import re
import time
import urllib.request
from pathlib import Path
from typing import Any

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

app = FastAPI(title="票迹真实展示价 API", version="1.0.0")
ROOT = Path(__file__).resolve().parents[1]
LOCK = asyncio.Lock()
CACHE: dict[str, tuple[float, dict[str, Any]]] = {}

CITY_CODES = {
    "北京":"BJS","上海":"SHA","广州":"CAN","深圳":"SZX","成都":"CTU","重庆":"CKG",
    "杭州":"HGH","南京":"NKG","武汉":"WUH","西安":"SIA","昆明":"KMG","长沙":"CSX",
    "厦门":"XMN","青岛":"TAO","天津":"TSN","郑州":"CGO","海口":"HAK","三亚":"SYX",
    "大连":"DLC","沈阳":"SHE","哈尔滨":"HRB","长春":"CGQ","济南":"TNA","福州":"FOC",
    "南宁":"NNG","贵阳":"KWE","乌鲁木齐":"URC","兰州":"LHW","银川":"INC","西宁":"XNN",
    "拉萨":"LXA","宁波":"NGB","温州":"WNZ","无锡":"WUX","珠海":"ZUH","石家庄":"SJW",
    "太原":"TYN","呼和浩特":"HET","合肥":"HFE","南昌":"KHN","桂林":"KWL","丽江":"LJG",
    "大理":"DLU","西双版纳":"JHG","张家界":"DYG","泉州":"JJN","烟台":"YNT","威海":"WEH"
}

class SearchRequest(BaseModel):
    from_city: str = Field(min_length=2, max_length=20)
    to_city: str = Field(min_length=2, max_length=20)
    date: dt.date
    passengers: int = Field(default=1, ge=1, le=9)

def minutes(value: str) -> int:
    hour, minute = (int(x) for x in value.split(":"))
    return hour * 60 + minute

def duration_minutes(depart: str, arrive: str) -> int:
    value = minutes(arrive) - minutes(depart)
    return value if value > 0 else value + 24 * 60

def public_html_text(raw: str) -> str:
    raw = re.sub(r"<(script|style)[^>]*>.*?</\\1>", " ", raw, flags=re.I | re.S)
    raw = re.sub(r"<[^>]+>", "\\n", raw)
    return html_lib.unescape(raw).replace("\\xa0", " ")

def fetch_public_html(url: str) -> str:
    request = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 Chrome/125 Mobile Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept": "text/html,application/xhtml+xml",
    })
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")

def parse_rows(text: str, source_url: str) -> list[dict[str, Any]]:
    normalized = re.sub(r"[*_#|]+", " ", text)
    normalized = re.sub(r"[ 	]+", " ", normalized)
    pattern = re.compile(
        r"(\d{2}:\d{2})\s*\n?\s*([^\n¥]{1,20}?)\s*\n?\s*[⇀→]\s*\n?\s*"
        r"(\d{2}:\d{2})\s*\n?\s*([^\n¥]{1,20}?)\s*\n?\s*¥\s*(\d{2,5})"
    )
    grouped: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for depart, dep_airport, arrive, arr_airport, price_raw in pattern.findall(normalized):
        dep_airport, arr_airport = dep_airport.strip(), arr_airport.strip()
        if len(dep_airport) > 16 or len(arr_airport) > 16:
            continue
        key = (depart, dep_airport, arrive, arr_airport)
        price = int(price_raw)
        quote = ["携程", price]
        if key not in grouped:
            grouped[key] = {
                "id": len(grouped) + 1,
                "airline": "公开航班",
                "code": "时刻与机场匹配",
                "logo": "航",
                "official": source_url,
                "depart": depart,
                "arrive": arrive,
                "departAirport": dep_airport,
                "arriveAirport": arr_airport,
                "duration": duration_minutes(depart, arrive),
                "airport": "主机场",
                "price": price,
                "score": 100 - len(grouped),
                "quotes": [quote],
                "dataKind": "real-public-display",
            }
        elif price < grouped[key]["price"]:
            grouped[key]["price"] = price
            grouped[key]["quotes"] = [quote]
    return sorted(grouped.values(), key=lambda row: (row["price"], row["depart"]))[:30]

async def fetch_ctrip(from_city: str, to_city: str, date: dt.date) -> dict[str, Any]:
    origin, destination = CITY_CODES.get(from_city), CITY_CODES.get(to_city)
    if not origin or not destination:
        raise HTTPException(422, detail="当前真实数据采集暂不支持该城市")
    day = (date - dt.date.today()).days
    if day < 0 or day > 89:
        raise HTTPException(422, detail="仅支持今天起 90 天内的日期")
    source_url = f"https://m.ctrip.com/html5/flight/{origin}-{destination}-day-{day}.html"
    flights: list[dict[str, Any]] = []
    channel = "public-html"
    try:
        raw_html = await asyncio.to_thread(fetch_public_html, source_url)
        flights = parse_rows(public_html_text(raw_html), source_url)
    except Exception:
        flights = []
    if not flights:
        channel = "crawl4ai-browser"
        browser = BrowserConfig(headless=True, browser_type="chromium")
        config = CrawlerRunConfig(
            page_timeout=60000,
            wait_until="domcontentloaded",
            delay_before_return_html=5.0,
            cache_mode=CacheMode.BYPASS,
        )
        async with AsyncWebCrawler(config=browser) as crawler:
            result = await crawler.arun(url=source_url, config=config)
        if result.success:
            markdown = getattr(result.markdown, "raw_markdown", None) or str(result.markdown)
            flights = parse_rows(markdown, source_url)
    if not flights:
        raise HTTPException(502, detail="第三方公开页可访问性受限，未取得可验证展示价")
    return {
        "live": True,
        "kind": "real-public-display",
        "source": "携程公开航线页",
        "sourceUrl": source_url,
        "route": {"from": from_city, "to": to_city},
        "date": date.isoformat(),
        "fetchedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "collectionChannel": channel,
        "notice": "以下为第三方公开页面当次展示价，可能随库存变化；点击平台后请再次核对。",
        "flights": flights,
    }

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

@app.post("/api/search")
async def search(payload: SearchRequest) -> dict[str, Any]:
    if payload.from_city == payload.to_city:
        raise HTTPException(422, detail="出发城市和到达城市不能相同")
    key = f"{payload.from_city}:{payload.to_city}:{payload.date.isoformat()}"
    cached = CACHE.get(key)
    if cached and time.time() - cached[0] < 300:
        return {**cached[1], "cached": True}
    async with LOCK:
        cached = CACHE.get(key)
        if cached and time.time() - cached[0] < 300:
            return {**cached[1], "cached": True}
        result = await fetch_ctrip(payload.from_city, payload.to_city, payload.date)
        CACHE[key] = (time.time(), result)
        return result

@app.get("/")
async def index() -> FileResponse:
    return FileResponse(ROOT / "index.html")
