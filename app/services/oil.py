import time
import logging
from datetime import date, timedelta
from typing import Dict, Any, List, Optional
import httpx

logger = logging.getLogger("onehub.oil")

EASTMONEY_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://data.eastmoney.com/",
    "Accept": "*/*"
}

# 兜底各省油价数据
FALLBACK_OIL_LIST = [
    {"city": "北京", "province": "北京", "date": "2026-08-29", "p92": 8.09, "p95": 8.61, "p89": 7.57, "p0": 7.81, "change92": 0.31, "change95": 0.33, "change0": 0.31, "prev92": 7.78, "prev95": 8.28, "prev0": 7.50},
    {"city": "上海", "province": "上海", "date": "2026-08-29", "p92": 8.05, "p95": 8.57, "p89": 7.51, "p0": 7.74, "change92": 0.31, "change95": 0.33, "change0": 0.31, "prev92": 7.74, "prev95": 8.24, "prev0": 7.43},
    {"city": "山东", "province": "山东", "date": "2026-08-29", "p92": 8.05, "p95": 8.64, "p89": 7.48, "p0": 7.68, "change92": 0.31, "change95": 0.33, "change0": 0.31, "prev92": 7.74, "prev95": 8.31, "prev0": 7.37},
    {"city": "广东", "province": "广东", "date": "2026-08-29", "p92": 8.11, "p95": 8.78, "p89": 7.52, "p0": 7.77, "change92": 0.31, "change95": 0.34, "change0": 0.31, "prev92": 7.80, "prev95": 8.44, "prev0": 7.46},
    {"city": "浙江", "province": "浙江", "date": "2026-08-29", "p92": 8.06, "p95": 8.57, "p89": 7.48, "p0": 7.74, "change92": 0.31, "change95": 0.33, "change0": 0.31, "prev92": 7.75, "prev95": 8.24, "prev0": 7.43},
    {"city": "江苏", "province": "江苏", "date": "2026-08-29", "p92": 8.06, "p95": 8.57, "p89": 7.59, "p0": 7.72, "change92": 0.31, "change95": 0.33, "change0": 0.31, "prev92": 7.75, "prev95": 8.24, "prev0": 7.41},
    {"city": "四川", "province": "四川", "date": "2026-08-29", "p92": 8.18, "p95": 8.75, "p89": 7.60, "p0": 7.81, "change92": 0.31, "change95": 0.33, "change0": 0.31, "prev92": 7.87, "prev95": 8.42, "prev0": 7.50},
    {"city": "湖北", "province": "湖北", "date": "2026-08-29", "p92": 8.10, "p95": 8.67, "p89": 7.52, "p0": 7.75, "change92": 0.31, "change95": 0.33, "change0": 0.31, "prev92": 7.79, "prev95": 8.34, "prev0": 7.44},
    {"city": "河南", "province": "河南", "date": "2026-08-29", "p92": 8.09, "p95": 8.64, "p89": 7.51, "p0": 7.74, "change92": 0.30, "change95": 0.32, "change0": 0.31, "prev92": 7.79, "prev95": 8.32, "prev0": 7.43},
    {"city": "河北", "province": "河北", "date": "2026-08-29", "p92": 8.08, "p95": 8.54, "p89": 7.50, "p0": 7.76, "change92": 0.30, "change95": 0.32, "change0": 0.31, "prev92": 7.78, "prev95": 8.22, "prev0": 7.45},
    {"city": "陕西", "province": "陕西", "date": "2026-08-29", "p92": 7.97, "p95": 8.42, "p89": 7.42, "p0": 7.65, "change92": 0.30, "change95": 0.32, "change0": 0.31, "prev92": 7.67, "prev95": 8.10, "prev0": 7.34},
    {"city": "重庆", "province": "重庆", "date": "2026-08-29", "p92": 8.15, "p95": 8.61, "p89": 7.58, "p0": 7.82, "change92": 0.31, "change95": 0.33, "change0": 0.31, "prev92": 7.84, "prev95": 8.28, "prev0": 7.51},
    {"city": "海南", "province": "海南", "date": "2026-08-29", "p92": 9.20, "p95": 9.77, "p89": 8.39, "p0": 7.84, "change92": 0.30, "change95": 0.32, "change0": 0.31, "prev92": 8.90, "prev95": 9.45, "prev0": 7.53}
]

# 2026 年成品油调价窗口（当日 24:00 执行、次日零点生效），用于推算下一个调价日
ADJUST_WINDOWS_2026 = [
    "2026-09-11", "2026-09-25", "2026-10-16",
    "2026-11-06", "2026-11-20", "2026-12-04", "2026-12-18"
]

def parse_date(value: Any) -> Optional[date]:
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None

def resolve_next_adjust_window(cycle_start: str) -> str:
    """按调价日历推算下一个调价窗口日，日历用尽时按 14 天周期顺延"""
    start = parse_date(cycle_start)
    if start:
        for window in ADJUST_WINDOWS_2026:
            window_date = parse_date(window)
            if window_date and window_date > start:
                return window
        return (start + timedelta(days=13)).isoformat()
    return ADJUST_WINDOWS_2026[0]

def build_adjust_advice(est_tons: float, next_window: str) -> str:
    window_date = parse_date(next_window)
    label = f"{window_date.month}月{window_date.day}日" if window_date else next_window
    if est_tons >= 50:
        return f"本轮国际原油走高，国内油价预计上调。建议山东车主在 {label} 24:00 前加满油箱，提前锁定优惠！"
    if est_tons <= -50:
        return f"本轮国际原油回落，国内油价预计下调，建议等到 {label} 调价落地后再加油更划算。"
    return "本轮国际原油波动未超过调价红线，预计搁浅，按需加油即可。"

# 内存 TTL 缓存
_prices_cache = {"data": None, "expires_at": 0}
_prediction_cache = {"data": None, "expires_at": 0}
_history_cache: Dict[str, Dict[str, Any]] = {}

def compute_summary(oil_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not oil_list:
        return {
            "avg92": 8.09, "avg95": 8.62, "avg0": 7.76,
            "max92": {"province": "海南", "price": 9.20},
            "min92": {"province": "陕西", "price": 7.97},
            "avgChange92": 0.31, "totalProvinces": 0
        }
    valid92 = [x for x in oil_list if x.get("p92", 0) > 0]
    valid95 = [x for x in oil_list if x.get("p95", 0) > 0]
    valid0 = [x for x in oil_list if x.get("p0", 0) > 0]

    sum92 = sum(x["p92"] for x in valid92)
    sum95 = sum(x["p95"] for x in valid95)
    sum0 = sum(x["p0"] for x in valid0)
    sumChange92 = sum(x.get("change92", 0) for x in valid92)

    sorted92 = sorted(valid92, key=lambda x: x["p92"])
    min92 = sorted92[0] if sorted92 else {"province": "陕西", "p92": 7.97}
    max92 = sorted92[-1] if sorted92 else {"province": "海南", "p92": 9.20}

    return {
        "avg92": round(sum92 / len(valid92), 2) if valid92 else 8.09,
        "avg95": round(sum95 / len(valid95), 2) if valid95 else 8.62,
        "avg0": round(sum0 / len(valid0), 2) if valid0 else 7.76,
        "max92": {"province": max92["province"], "price": max92["p92"]},
        "min92": {"province": min92["province"], "price": min92["p92"]},
        "avgChange92": round(sumChange92 / len(valid92), 2) if valid92 else 0.31,
        "totalProvinces": len(oil_list)
    }

async def get_national_oil_prices() -> Dict[str, Any]:
    """获取全国各省最新油价（带 2 小时缓存）"""
    now = time.time()
    if _prices_cache["data"] and now < _prices_cache["expires_at"]:
        return _prices_cache["data"]

    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    params = {
        "reportName": "RPTA_WEB_YJ_JH",
        "columns": "ALL",
        "sortColumns": "DIM_DATE",
        "sortTypes": "-1",
        "pageNumber": "1",
        "pageSize": "40"
    }

    oil_list = []
    updated_at = ""
    data_source = "eastmoney"

    try:
        async with httpx.AsyncClient(headers=EASTMONEY_HEADERS, timeout=8.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                if data and data.get("success") and data.get("result"):
                    # 同一省份会返回多期历史数据，按省份只保留调价日期最新的一条
                    latest_by_city: Dict[str, Dict[str, Any]] = {}
                    for item in data["result"].get("data", []):
                        city = item.get("CITYNAME")
                        if not city:
                            continue
                        d_str = str(item.get("DIM_DATE", ""))[:10]
                        existed = latest_by_city.get(city)
                        if existed and existed["date"] >= d_str:
                            continue
                        latest_by_city[city] = {
                            "city": city,
                            "province": city,
                            "date": d_str,
                            "p92": float(item.get("V92") or 0),
                            "p95": float(item.get("V95") or 0),
                            "p89": float(item.get("V89") or 0),
                            "p0": float(item.get("V0") or 0),
                            "change92": float(item.get("ZDE92") or 0),
                            "change95": float(item.get("ZDE95") or 0),
                            "change0": float(item.get("ZDE0") or 0),
                            "prev92": float(item.get("QE92") or 0),
                            "prev95": float(item.get("QE95") or 0),
                            "prev0": float(item.get("QE0") or 0)
                        }
                    oil_list = sorted(latest_by_city.values(), key=lambda x: x["date"], reverse=True)
                    if oil_list:
                        updated_at = oil_list[0]["date"]
    except Exception as e:
        logger.warning(f"抓取东方财富油价接口失败，使用备用兜底数据: {e}")

    if not oil_list:
        oil_list = list(FALLBACK_OIL_LIST)
        updated_at = FALLBACK_OIL_LIST[0]["date"]
        data_source = "fallback"
        logger.warning("东方财富油价数据不可用，当前返回内置兜底数据，价格可能已过期")

    result = {
        "list": oil_list,
        "updatedAt": updated_at or FALLBACK_OIL_LIST[0]["date"],
        "dataSource": data_source,
        "summary": compute_summary(oil_list)
    }

    _prices_cache["data"] = result
    _prices_cache["expires_at"] = now + 7200  # 缓存 2 小时
    return result

async def get_oil_prediction() -> Dict[str, Any]:
    """推算未来油价涨跌预测（带 1 小时缓存）"""
    now = time.time()
    if _prediction_cache["data"] and now < _prediction_cache["expires_at"]:
        return _prediction_cache["data"]

    # 本周期起始日 = 最近一次调价执行日，直接取最新油价数据的日期，避免写死日期
    prices = await get_national_oil_prices()
    cycle_start = str(prices.get("updatedAt") or FALLBACK_OIL_LIST[0]["date"])
    next_window = resolve_next_adjust_window(cycle_start)
    window_date = parse_date(next_window)
    next_adjustment = f"{next_window} 24:00"
    next_effective = f"{(window_date + timedelta(days=1)).isoformat()} 00:00" if window_date else next_adjustment
    current_92 = float(next((x.get("p92") for x in prices.get("list", []) if x.get("province") == "山东"), 0) or 0)

    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    params = {
        "reportName": "RPTA_WEB_JY_HQ",
        "columns": "ALL",
        "sortColumns": "DATE",
        "sortTypes": "-1",
        "pageSize": "40",
        "pageNumber": "1"
    }

    try:
        async with httpx.AsyncClient(headers=EASTMONEY_HEADERS, timeout=8.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                raw_quotes = data.get("result", {}).get("data", []) if data.get("success") else []
                all_quotes = sorted(raw_quotes, key=lambda x: str(x.get("DATE", "")))
                # 只统计本调价周期（最近一次执行日之后）的三地原油收盘价
                cycle_quotes = [q for q in all_quotes if str(q.get("DATE", ""))[:10] >= cycle_start]
                if len(cycle_quotes) < 2:
                    cycle_quotes = all_quotes[-5:]
                if len(cycle_quotes) >= 2:
                    base_price = float(cycle_quotes[0].get("CLOSE") or 0)
                    recent_quotes = cycle_quotes[1:]
                    avg_recent = sum(float(q.get("CLOSE") or 0) for q in recent_quotes) / len(recent_quotes)
                    rate = ((avg_recent - base_price) / base_price) * 100 if base_price else 0.0

                    est_tons = round(rate * 36)
                    est_liter = round(est_tons * 0.00078, 2)

                    trend_status = "hold"
                    trend_label = "预计搁浅 (波动未超50元/吨)"
                    if est_tons >= 50:
                        trend_status = "up"
                        trend_label = "预计大幅上调" if est_tons >= 200 else "预计小幅上调"
                    elif est_tons <= -50:
                        trend_status = "down"
                        trend_label = "预计大幅下调" if est_tons <= -200 else "预计小幅下调"

                    working_day = min(10, len(cycle_quotes))

                    prediction = {
                        "cycleStartDate": cycle_start,
                        "nextAdjustmentDate": next_adjustment,
                        "nextEffectiveDate": next_effective,
                        "workingDay": working_day,
                        "workingDayTotal": 10,
                        "baseCrude": round(base_price, 2),
                        "currentCrudeAvg": round(avg_recent, 2),
                        "crudeChangeRate": round(rate, 2),
                        "estimatedChangeTons": est_tons,
                        "estimatedChangeLiter": est_liter,
                        "trendStatus": trend_status,
                        "trendLabel": trend_label,
                        "isExceedThreshold": abs(est_tons) >= 50,
                        "crudeDailyList": [
                            {"date": str(q.get("DATE", ""))[5:10], "close": float(q.get("CLOSE") or 0)}
                            for q in cycle_quotes
                        ],
                        "shandongImpact": {
                            "current92": current_92,
                            "predicted92": round(current_92 + est_liter, 2),
                            "diffTank50L": round(est_liter * 50, 2),
                            "advice": build_adjust_advice(est_tons, next_window)
                        }
                    }
                    _prediction_cache["data"] = prediction
                    _prediction_cache["expires_at"] = now + 3600
                    return prediction
    except Exception as e:
        logger.warning(f"推算油价预测异常，使用基准模型: {e}")

    # 兜底预测
    fallback_prediction = {
        "cycleStartDate": cycle_start,
        "nextAdjustmentDate": next_adjustment,
        "nextEffectiveDate": next_effective,
        "workingDay": 1,
        "workingDayTotal": 10,
        "baseCrude": 83.44,
        "currentCrudeAvg": 91.77,
        "crudeChangeRate": 9.98,
        "estimatedChangeTons": 360,
        "estimatedChangeLiter": 0.28,
        "trendStatus": "up",
        "trendLabel": "预计大幅上调",
        "isExceedThreshold": True,
        "crudeDailyList": [
            {"date": "08-28", "close": 83.44},
            {"date": "08-31", "close": 86.31},
            {"date": "09-01", "close": 90.68},
            {"date": "09-02", "close": 90.63},
            {"date": "09-03", "close": 91.67},
            {"date": "09-04", "close": 91.22},
            {"date": "09-07", "close": 92.70},
            {"date": "09-08", "close": 94.25},
            {"date": "09-09", "close": 96.67}
        ],
        "shandongImpact": {
            "current92": current_92,
            "predicted92": round(current_92 + 0.28, 2),
            "diffTank50L": 14.00,
            "advice": build_adjust_advice(360, next_window)
        }
    }
    _prediction_cache["data"] = fallback_prediction
    _prediction_cache["expires_at"] = now + 3600
    return fallback_prediction

async def get_city_oil_history(city_name: str) -> List[Dict[str, Any]]:
    """获取指定城市调价历史"""
    now = time.time()
    if city_name in _history_cache and now < _history_cache[city_name]["expires_at"]:
        return _history_cache[city_name]["data"]

    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    params = {
        "reportName": "RPTA_WEB_YJ_JH",
        "columns": "ALL",
        "filter": f'(CITYNAME="{city_name}")',
        "sortColumns": "DIM_DATE",
        "sortTypes": "-1",
        "pageSize": "10",
        "pageNumber": "1"
    }

    history = []
    try:
        async with httpx.AsyncClient(headers=EASTMONEY_HEADERS, timeout=6.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("result", {}).get("data", []) if data.get("success") else []
                for item in items:
                    history.append({
                        "date": str(item.get("DIM_DATE", ""))[:10],
                        "p92": float(item.get("V92") or 0),
                        "p95": float(item.get("V95") or 0),
                        "p0": float(item.get("V0") or 0),
                        "change92": float(item.get("ZDE92") or 0)
                    })
    except Exception as e:
        logger.warning(f"获取 {city_name} 历史调价失败: {e}")

    if not history:
        history = [
            {"date": "2026-08-29", "p92": 8.05, "p95": 8.64, "p0": 7.68, "change92": 0.31},
            {"date": "2026-08-15", "p92": 7.74, "p95": 8.31, "p0": 7.37, "change92": -0.19},
            {"date": "2026-08-01", "p92": 7.93, "p95": 8.50, "p0": 7.56, "change92": 0.55},
            {"date": "2026-07-18", "p92": 7.38, "p95": 7.92, "p0": 7.01, "change92": 0.24},
            {"date": "2026-07-04", "p92": 7.14, "p95": 7.66, "p0": 6.77, "change92": -0.76}
        ]

    _history_cache[city_name] = {"data": history, "expires_at": now + 21600}
    return history
