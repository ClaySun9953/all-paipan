# location_data.py
# -*- coding: utf-8 -*-

"""
地点数据模块。

CITY_DATA 保存明确城市的：
- 经度
- 纬度
- IANA 时区
- 时区标准子午线

未知地点不会自动使用北京、哈尔滨或其他默认坐标。
"""

from typing import Any, Dict


CITY_DATA: Dict[str, Dict[str, Any]] = {
    "北京": {
        "longitude": 116.4074,
        "latitude": 39.9042,
        "timezone": "Asia/Shanghai",
        "standard_meridian": 120.0,
    },
    "哈尔滨": {
        "longitude": 126.6276,
        "latitude": 45.8038,
        "timezone": "Asia/Shanghai",
        "standard_meridian": 120.0,
    },
    "深圳": {
        "longitude": 114.0579,
        "latitude": 22.5431,
        "timezone": "Asia/Shanghai",
        "standard_meridian": 120.0,
    },
    "成都": {
        "longitude": 104.0665,
        "latitude": 30.5723,
        "timezone": "Asia/Shanghai",
        "standard_meridian": 120.0,
    },
    "齐齐哈尔": {
        "longitude": 123.9182,
        "latitude": 47.3549,
        "timezone": "Asia/Shanghai",
        "standard_meridian": 120.0,
    },
    "佳木斯": {
        "longitude": 130.3616,
        "latitude": 46.8028,
        "timezone": "Asia/Shanghai",
        "standard_meridian": 120.0,
    },
    "上海": {
        "longitude": 121.4737,
        "latitude": 31.2304,
        "timezone": "Asia/Shanghai",
        "standard_meridian": 120.0,
    },
    "广州": {
        "longitude": 113.2644,
        "latitude": 23.1291,
        "timezone": "Asia/Shanghai",
        "standard_meridian": 120.0,
    },
    "纽约": {
        "longitude": -74.0060,
        "latitude": 40.7128,
        "timezone": "America/New_York",
        "standard_meridian": -75.0,
    },
    "洛杉矶": {
        "longitude": -118.2437,
        "latitude": 34.0522,
        "timezone": "America/Los_Angeles",
        "standard_meridian": -120.0,
    },
    "伦敦": {
        "longitude": -0.1276,
        "latitude": 51.5072,
        "timezone": "Europe/London",
        "standard_meridian": 0.0,
    },
    "东京": {
        "longitude": 139.6917,
        "latitude": 35.6895,
        "timezone": "Asia/Tokyo",
        "standard_meridian": 135.0,
    },
    "悉尼": {
        "longitude": 151.2093,
        "latitude": -33.8688,
        "timezone": "Australia/Sydney",
        "standard_meridian": 150.0,
    },
}


def get_city_data(city_name: str) -> dict:
    """获取城市信息。城市不存在时直接报错。"""
    if city_name not in CITY_DATA:
        raise ValueError(f"城市不在地点数据库中：{city_name}")

    return CITY_DATA[city_name]


def validate_coordinates(
    longitude: float,
    latitude: float,
) -> None:
    """校验经纬度范围。"""
    longitude = float(longitude)
    latitude = float(latitude)

    if not -180.0 <= longitude <= 180.0:
        raise ValueError("经度必须在 -180 至 180 度之间。")

    if not -90.0 <= latitude <= 90.0:
        raise ValueError("纬度必须在 -90 至 90 度之间。")
