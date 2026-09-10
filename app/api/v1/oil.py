from fastapi import APIRouter, Query
from app.services.oil import (
    get_national_oil_prices,
    get_oil_prediction,
    get_city_oil_history
)

router = APIRouter(prefix="/oil", tags=["成品油价格查询与预测"])

@router.get("/prices", summary="获取全国各省成品油最新价格及统计分析")
async def get_oil_prices():
    """获取全国 31 省市最新 92#、95#、0# 柴油牌价及均价走势（后端带 2 小时缓存）"""
    data = await get_national_oil_prices()
    return {"code": 200, "message": "success", "data": data}

@router.get("/prediction", summary="获取国际原油走势推算及下轮调价涨跌预测")
async def get_prediction():
    """推算当前调价窗口工作日进度、三地原油变化率、吨/升调价预估值及加满油箱建议（后端带 1 小时缓存）"""
    data = await get_oil_prediction()
    return {"code": 200, "message": "success", "data": data}

@router.get("/history/{city_name}", summary="获取指定省市成品油历史调价记录")
async def get_oil_history(city_name: str):
    """获取指定省市近 5~10 轮成品油调价历史明细"""
    data = await get_city_oil_history(city_name)
    return {"code": 200, "message": "success", "data": data}
