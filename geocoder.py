# geocoder.py
# -*- coding: utf-8 -*-

"""
地址地理编码模块。

优先使用高德地图：
- 适合中文地址；
- 返回坐标通常为 GCJ-02。

没有配置高德 Key 时，备用使用 Nominatim：
- 返回坐标通常为 WGS-84；
- 适合全球地址；
- 有访问频率限制。

地址无法识别时返回 None，不使用默认坐标。
"""

import os
from typing import Optional

import requests
import streamlit as st
from geopy.geocoders import Nominatim


def get_amap_key() -> str:
    """优先从 Streamlit secrets 获取，再读取环境变量。"""
    try:
        secret_key = st.secrets.get("AMAP_API_KEY", "")
    except Exception:
        secret_key = ""

    return (
        str(secret_key or os.getenv("AMAP_API_KEY", ""))
        .strip()
    )


@st.cache_data(show_spinner=False, ttl=86400)
def geocode_with_amap(
    address: str,
    city: str = "",
) -> Optional[dict]:
    """使用高德地图地址转经纬度。"""
    api_key = get_amap_key()

    if not api_key:
        return None

    address = address.strip()

    if not address:
        return None

    url = "https://restapi.amap.com/v3/geocode/geo"

    params = {
        "key": api_key,
        "address": address,
        "city": city.strip(),
        "output": "JSON",
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=8,
        )
        response.raise_for_status()
        data = response.json()
    except (
        requests.RequestException,
        ValueError,
    ):
        return None

    if data.get("status") != "1":
        return None

    geocodes = data.get("geocodes") or []

    if not geocodes:
        return None

    item = geocodes[0]
    location = item.get("location", "")

    if "," not in location:
        return None

    try:
        lon_text, lat_text = location.split(",", 1)
        longitude = float(lon_text)
        latitude = float(lat_text)
    except (TypeError, ValueError):
        return None

    return {
        "provider": "amap",
        "address": item.get(
            "formatted_address",
            address,
        ),
        "longitude": longitude,
        "latitude": latitude,
        "coordinate_system": "GCJ-02",
    }


@st.cache_data(show_spinner=False, ttl=86400)
def geocode_with_nominatim(
    address: str,
) -> Optional[dict]:
    """使用 OpenStreetMap Nominatim 地址转经纬度。"""
    address = address.strip()

    if not address:
        return None

    try:
        geolocator = Nominatim(
            user_agent="cyber_metaphysics_v35",
        )

        location = geolocator.geocode(
            address,
            exactly_one=True,
            timeout=8,
        )
    except Exception:
        return None

    if location is None:
        return None

    try:
        longitude = float(location.longitude)
        latitude = float(location.latitude)
    except (TypeError, ValueError):
        return None

    return {
        "provider": "nominatim",
        "address": location.address or address,
        "longitude": longitude,
        "latitude": latitude,
        "coordinate_system": "WGS-84",
    }


def geocode_address(
    address: str,
    city: str = "",
    use_nominatim_fallback: bool = True,
) -> Optional[dict]:
    """
    地址解析总入口。

    顺序：
    1. 高德；
    2. Nominatim。

    无法识别时返回 None。
    """
    address = address.strip()

    if not address:
        return None

    result = geocode_with_amap(
        address=address,
        city=city,
    )

    if result is not None:
        return result

    if use_nominatim_fallback:
        return geocode_with_nominatim(address)

    return None
