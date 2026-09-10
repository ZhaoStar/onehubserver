from fastapi import APIRouter, Query
from app.services.weather import (
    get_city_weather_data,
    fetch_weather_alerts,
    DEFAULT_CITY,
    CITIES_CONFIG
)

router = APIRouter(prefix="/weather", tags=["开源天气与气象灾害预警"])

@router.get("/data", summary="获取指定城市完整气象数据（实况+7天预报+空气质量+预警）")
async def get_weather(city: str = Query(DEFAULT_CITY, description="城市名称，如：青岛、济南、北京")):
    """获取指定城市气温、体感、湿度、风力、AQI 空气质量指数、未来 7 天预报与中央气象台突发灾害预警（后端带 15 分钟缓存）"""
    data = await get_city_weather_data(city)
    return {"code": 200, "message": "success", "data": data}

@router.get("/alerts", summary="获取指定城市气象灾害预警")
async def get_alerts(city: str = Query(DEFAULT_CITY, description="城市名称")):
    """查询指定地区当前生效的气象灾害预警（台风、暴雨、雷电、大风、高温、寒潮等）"""
    data = await fetch_weather_alerts(city)
    return {"code": 200, "message": "success", "data": data}

@router.get("/cities", summary="获取支持预置城市列表")
async def get_cities():
    """获取支持预置经纬度及编码的城市字典"""
    return {"code": 200, "message": "success", "data": list(CITIES_CONFIG.values())}
