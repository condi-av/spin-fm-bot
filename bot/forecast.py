import aiohttp, math, os
from typing import Dict
from .coords import COORDS

OPENWEATHER_KEY = os.getenv("OPENWEATHER_KEY")

async def get_forecast(region: str) -> Dict:
    lat, lon = COORDS[region]
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_KEY}&units=metric"
    async with aiohttp.ClientSession() as s:
        async with s.get(url) as r:
            data = await r.json()
    temp = data["main"]["temp"]
    pressure = round(data["main"]["pressure"] * 0.750064)   # гПа → мм рт. ст.
    moon = moon_percent()
    score = bite_score(temp, pressure, moon)
    advice = "Клёв отличный!" if score > 75 else "Клёв слабый – берите прикормку." if score < 40 else "Клёв средний."
    return {
        "region": region,
        "temp": temp,
        "pressure": pressure,
        "moon": moon,
        "score": score,
        "advice": advice
    }

def moon_percent() -> float:
    day = datetime.datetime.now().day
    return round((1 - math.cos(2 * math.pi * day / 29.5)) / 2 * 100)

def bite_score(temp: float, pressure: int, moon: float) -> int:
    s = 50
    if 5 <= temp <= 15: s += 15
    if 750 <= pressure <= 770: s += 15
    if 20 <= moon <= 80: s += 10
    return max(0, min(100, s))
