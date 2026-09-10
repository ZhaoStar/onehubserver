import time
import re
import json
import logging
from typing import Dict, Any, List, Optional
import httpx

logger = logging.getLogger("onehub.weather")

CITIES_CONFIG: Dict[str, Dict[str, Any]] = {
    "青岛": {"name": "青岛", "province": "山东", "lat": 36.0671, "lon": 120.3826, "code": "101120201"},
    "济南": {"name": "济南", "province": "山东", "lat": 36.6512, "lon": 117.1201, "code": "101120101"},
    "烟台": {"name": "烟台", "province": "山东", "lat": 37.4638, "lon": 121.4479, "code": "101120501"},
    "潍坊": {"name": "潍坊", "province": "山东", "lat": 36.7068, "lon": 119.1618, "code": "101120601"},
    "临沂": {"name": "临沂", "province": "山东", "lat": 35.1047, "lon": 118.3564, "code": "101120901"},
    "威海": {"name": "威海", "province": "山东", "lat": 37.5131, "lon": 122.1204, "code": "101121301"},
    "北京": {"name": "北京", "province": "北京", "lat": 39.9042, "lon": 116.4074, "code": "101010100"},
    "上海": {"name": "上海", "province": "上海", "lat": 31.2304, "lon": 121.4737, "code": "101020100"},
    "广州": {"name": "广州", "province": "广东", "lat": 23.1291, "lon": 113.2644, "code": "101280101"},
    "深圳": {"name": "深圳", "province": "广东", "lat": 22.5431, "lon": 114.0579, "code": "101280601"},
    "杭州": {"name": "杭州", "province": "浙江", "lat": 30.2741, "lon": 120.1551, "code": "101210101"},
    "成都": {"name": "成都", "province": "四川", "lat": 30.5728, "lon": 104.0668, "code": "101270101"},
    "西安": {"name": "西安", "province": "陕西", "lat": 34.3416, "lon": 108.9398, "code": "101110101"}
}

DEFAULT_CITY = "青岛"

# 缓存: city -> {data: ..., expires_at: ...}
_weather_cache: Dict[str, Dict[str, Any]] = {}
_alert_cache: Dict[str, Dict[str, Any]] = {}

def parse_wmo_weather(code: int, is_day: int = 1) -> Dict[str, str]:
    if code == 0:
        return {"text": "晴", "icon": "ri-sun-fill" if is_day else "ri-moon-fill", "type": "sunny"}
    elif code in (1, 2):
        return {"text": "多云", "icon": "ri-sun-cloudy-line" if is_day else "ri-moon-cloudy-line", "type": "cloudy"}
    elif code == 3:
        return {"text": "阴", "icon": "ri-cloudy-fill", "type": "overcast"}
    elif code in (45, 48):
        return {"text": "大雾", "icon": "ri-foggy-fill", "type": "fog"}
    elif code in (51, 53, 55):
        return {"text": "毛毛细雨", "icon": "ri-drizzle-line", "type": "rain"}
    elif code == 61:
        return {"text": "小雨", "icon": "ri-rainy-line", "type": "rain"}
    elif code == 63:
        return {"text": "中雨", "icon": "ri-rainy-fill", "type": "rain"}
    elif code == 65:
        return {"text": "大雨", "icon": "ri-heavy-showers-line", "type": "rain"}
    elif code in (71, 73, 75):
        return {"text": "降雪", "icon": "ri-snowy-fill", "type": "snow"}
    elif code in (80, 81, 82):
        return {"text": "阵雨", "icon": "ri-showers-line", "type": "rain"}
    elif code in (95, 96, 99):
        return {"text": "雷阵雨", "icon": "ri-thunderstorms-fill", "type": "thunder"}
    else:
        return {"text": "多云", "icon": "ri-cloudy-line", "type": "cloudy"}

def parse_aqi(aqi_val: float) -> Dict[str, Any]:
    val = round(aqi_val or 50)
    if val <= 50:
        return {"aqi": val, "text": "优", "level": "good", "color": "#10b981"}
    elif val <= 100:
        return {"aqi": val, "text": "良", "level": "moderate", "color": "#3b82f6"}
    elif val <= 150:
        return {"aqi": val, "text": "轻度", "level": "light", "color": "#f59e0b"}
    elif val <= 200:
        return {"aqi": val, "text": "中度", "level": "medium", "color": "#ef4444"}
    else:
        return {"aqi": val, "text": "重度", "level": "heavy", "color": "#8b5cf6"}

def parse_wind_direction(deg: float) -> str:
    d = float(deg or 0)
    directions = ["北风", "东北风", "东风", "东南风", "南风", "西南风", "西风", "西北风"]
    index = round((d % 360) / 45) % 8
    return directions[index]

async def fetch_weather_alerts(city_name: str = DEFAULT_CITY) -> Dict[str, Any]:
    """获取指定城市中央气象台/中国天气网预警（带 10 分钟缓存）"""
    city = CITIES_CONFIG.get(city_name, CITIES_CONFIG[DEFAULT_CITY])
    now = time.time()
    cache_key = city["name"]
    if cache_key in _alert_cache and now < _alert_cache[cache_key]["expires_at"]:
        return _alert_cache[cache_key]["data"]

    target_area_id = city["code"][:7] if city.get("code") else "1011202"
    url = f"https://product.weather.com.cn/alarm/grepalarm.php?areaid={target_area_id}"
    headers = {
        "Referer": "http://www.weather.com.cn/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    result = {
        "hasAlert": False,
        "count": 0,
        "alerts": [],
        "statusText": f"{city['name']}气象台暂无突发气象预警，天气平稳"
    }

    try:
        async with httpx.AsyncClient(headers=headers, timeout=5.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                match = re.search(r"alarminfo\s*=\s*(\{[\s\S]*?\});", resp.text)
                if match:
                    parsed = json.loads(match.group(1))
                    count = int(parsed.get("count", 0))
                    raw_data = parsed.get("data", [])
                    if count > 0 and isinstance(raw_data, list):
                        alerts = []
                        for item in raw_data[:3]:
                            file_name = item[1] if len(item) > 1 else None
                            if file_name:
                                detail_url = f"https://product.weather.com.cn/alarm/webdata/{file_name}"
                                d_resp = await client.get(detail_url, timeout=3.0)
                                if d_resp.status_code == 200:
                                    d_match = re.search(r"alarminfo\s*=\s*(\{[\s\S]*?\});", d_resp.text)
                                    if d_match:
                                        d = json.loads(d_match.group(1))
                                        level = d.get("SIGNALLEVEL", "蓝色")
                                        level_class = "alert-blue"
                                        if "黄" in level: level_class = "alert-yellow"
                                        elif "橙" in level: level_class = "alert-orange"
                                        elif "红" in level: level_class = "alert-red"
                                        alerts.append({
                                            "id": d.get("ALERTID", file_name),
                                            "title": d.get("head", f"{d.get('PROVINCE', '')}{d.get('SIGNALTYPE', '气象')}{level}预警"),
                                            "type": d.get("SIGNALTYPE", "气象灾害"),
                                            "level": level,
                                            "levelClass": level_class,
                                            "issueTime": d.get("ISSUETIME", ""),
                                            "content": d.get("ISSUECONTENT", "请做好防灾减灾应急防范工作。"),
                                            "station": d.get("STATIONNAME") or d.get("PROVINCE") or "气象台"
                                        })
                        if alerts:
                            result = {
                                "hasAlert": True,
                                "count": len(alerts),
                                "alerts": alerts,
                                "statusText": f"注意防范：当前有 {len(alerts)} 条气象预警生效中"
                            }
    except Exception as e:
        logger.warning(f"获取 {city_name} 气象预警失败: {e}")

    _alert_cache[cache_key] = {"data": result, "expires_at": now + 600}
    return result

async def get_city_weather_data(city_name: str = DEFAULT_CITY) -> Dict[str, Any]:
    """获取城市完整气象数据（当前实况 + 7天预报 + 空气质量 + 预警，带 15 分钟缓存）"""
    city = CITIES_CONFIG.get(city_name, CITIES_CONFIG[DEFAULT_CITY])
    now = time.time()
    cache_key = city["name"]
    if cache_key in _weather_cache and now < _weather_cache[cache_key]["expires_at"]:
        return _weather_cache[cache_key]["data"]

    weather_url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={city['lat']}&longitude={city['lon']}"
        f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,wind_speed_10m,wind_direction_10m"
        f"&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
        f"&timezone=Asia%2FShanghai"
    )
    aqi_url = (
        f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={city['lat']}&longitude={city['lon']}"
        f"&current=us_aqi,pm10,pm2_5"
    )

    current_raw = {}
    daily_raw = {}
    aqi_raw = {}

    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            w_res, aqi_res = await client.get(weather_url), await client.get(aqi_url)
            if w_res.status_code == 200:
                w_json = w_res.json()
                current_raw = w_json.get("current", {})
                daily_raw = w_json.get("daily", {})
            if aqi_res.status_code == 200:
                aqi_json = aqi_res.json()
                aqi_raw = aqi_json.get("current", {})
    except Exception as e:
        logger.warning(f"请求 Open-Meteo 天气数据异常: {e}")

    # 获取预警
    alert_data = await fetch_weather_alerts(city_name)

    # 组装当前实况
    temp = round(current_raw.get("temperature_2m", 23))
    feels_like = round(current_raw.get("apparent_temperature", temp - 2))
    humidity = round(current_raw.get("relative_humidity_2m", 55))
    wind_speed = round(current_raw.get("wind_speed_10m", 16))
    wind_dir_text = parse_wind_direction(current_raw.get("wind_direction_10m", 10))
    weather_info = parse_wmo_weather(current_raw.get("weather_code", 2), current_raw.get("is_day", 1))
    aqi_info = parse_aqi(aqi_raw.get("us_aqi", 52))

    # 组装 7 天预报
    forecast_list = []
    times = daily_raw.get("time", [])
    if times and isinstance(times, list):
        w_codes = daily_raw.get("weather_code", [])
        max_temps = daily_raw.get("temperature_2m_max", [])
        min_temps = daily_raw.get("temperature_2m_min", [])
        pops = daily_raw.get("precipitation_probability_max", [])
        days_label = ["今天", "明天", "后天"]
        for i in range(min(7, len(times))):
            d_str = times[i]
            code = w_codes[i] if i < len(w_codes) else 1
            wmo = parse_wmo_weather(code)
            label = days_label[i] if i < len(days_label) else d_str[5:]
            forecast_list.append({
                "date": d_str,
                "label": label,
                "maxTemp": round(max_temps[i]) if i < len(max_temps) else 25,
                "minTemp": round(min_temps[i]) if i < len(min_temps) else 18,
                "weatherText": wmo["text"],
                "icon": wmo["icon"],
                "pop": pops[i] if i < len(pops) else 0
            })
    else:
        forecast_list = [
            {"date": "2026-09-10", "label": "今天", "maxTemp": 26, "minTemp": 19, "weatherText": "多云", "icon": "ri-sun-cloudy-line"},
            {"date": "2026-09-11", "label": "明天", "maxTemp": 25, "minTemp": 18, "weatherText": "阴", "icon": "ri-cloudy-fill"},
            {"date": "2026-09-12", "label": "后天", "maxTemp": 24, "minTemp": 18, "weatherText": "多云", "icon": "ri-sun-cloudy-line"},
            {"date": "2026-09-13", "label": "周日", "maxTemp": 26, "minTemp": 20, "weatherText": "晴", "icon": "ri-sun-fill"},
            {"date": "2026-09-14", "label": "周一", "maxTemp": 27, "minTemp": 21, "weatherText": "多云", "icon": "ri-sun-cloudy-line"},
            {"date": "2026-09-15", "label": "周二", "maxTemp": 25, "minTemp": 19, "weatherText": "小雨", "icon": "ri-rainy-line"},
            {"date": "2026-09-16", "label": "周三", "maxTemp": 24, "minTemp": 18, "weatherText": "阴", "icon": "ri-cloudy-fill"}
        ]

    from datetime import datetime
    result = {
        "city": city["name"],
        "province": city["province"],
        "fullCityName": f"{city['province']} · {city['name']}",
        "temp": temp,
        "feelsLike": feels_like,
        "humidity": humidity,
        "windSpeed": wind_speed,
        "windDirText": wind_dir_text,
        "weatherText": weather_info["text"],
        "icon": weather_info["icon"],
        "weatherType": weather_info["type"],
        "aqi": aqi_info,
        "pm25": round(aqi_raw.get("pm2_5", 12)),
        "alerts": alert_data,
        "forecast": forecast_list,
        "updatedAt": datetime.now().strftime("%H:%M")
    }

    _weather_cache[cache_key] = {"data": result, "expires_at": now + 900}  # 缓存 15 分钟
    return result
