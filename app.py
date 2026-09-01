# app.py
# -*- coding: utf-8 -*-
import core_engine
import datetime
import math
import random
from datetime import timedelta

import pytz
import streamlit as st
from timezonefinder import TimezoneFinder

from core_engine import (
    LiuYaoEngine,
    PrecisionSolarEngine,
    QimenEngine,
    TimeAndGeo,
)
from geocoder import geocode_address
from liuren_engine import DaLiuRenEngine
from location_data import (
    CITY_DATA,
    get_city_data,
    validate_coordinates,
)
from ziwei_engine import ZiWeiEngine


st.set_page_config(
    page_title="赛博玄学 V36.2",
    layout="wide",
    page_icon="🧿",
)

ZHI_NAMES = list("子丑寅卯辰巳午未申酉戌亥")


def year_to_zhi(year):
    """把出生年份换算成年命地支。"""
    try:
        year = int(year)
    except (TypeError, ValueError):
        return None

    return ZHI_NAMES[(year - 4) % 12]


def get_equation_of_time(dt):
    """NOAA 均时差，返回分钟。"""
    day_of_year = dt.timetuple().tm_yday - 1

    hour = (
        dt.hour
        + dt.minute / 60.0
        + dt.second / 3600.0
    )

    gamma = (
        2.0
        * math.pi
        / 365.24
        * (day_of_year + (hour - 12.0) / 24.0)
    )

    return 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )


def localize_datetime(timezone_name, naive_dt):
    """将输入时间解释为指定时区的当地民用时间。"""
    timezone = pytz.timezone(timezone_name)

    try:
        return timezone.localize(
            naive_dt,
            is_dst=None,
        )
    except pytz.AmbiguousTimeError as exc:
        raise ValueError(
            "该时间处于夏令时重复时段，无法唯一确定。"
        ) from exc
    except pytz.NonExistentTimeError as exc:
        raise ValueError(
            "该时间在当地不存在，通常由夏令时跳时造成。"
        ) from exc


def get_standard_meridian(timezone_name, local_dt_aware):
    """获取时区标准子午线。"""
    timezone = pytz.timezone(timezone_name)
    offsets = []

    for month in [1, 4, 7, 10]:
        probe = datetime.datetime(
            local_dt_aware.year,
            month,
            1,
            12,
            0,
            0,
        )

        try:
            probe_aware = timezone.localize(
                probe,
                is_dst=False,
            )
        except (
            pytz.AmbiguousTimeError,
            pytz.NonExistentTimeError,
        ):
            continue

        offset = probe_aware.utcoffset()

        if offset is not None:
            offsets.append(
                offset.total_seconds() / 3600.0
            )

    if not offsets:
        current_offset = local_dt_aware.utcoffset()

        if current_offset is None:
            raise ValueError(
                f"无法读取时区 {timezone_name} 的 UTC 偏移。"
            )

        return (
            current_offset.total_seconds() / 3600.0
        ) * 15.0

    return min(
        offsets,
        key=lambda value: abs(value),
    ) * 15.0


def safe_text(value, fallback="未提供"):
    """安全显示空值。"""
    if value is None:
        return fallback

    if isinstance(value, str):
        return value.strip() or fallback

    if isinstance(value, (list, tuple)):
        if not value:
            return fallback

        return "、".join(
            str(item)
            for item in value
        )

    return str(value)


def marker_text(marker):
    """格式化奇门落宫标记。"""
    if not isinstance(marker, dict):
        return "未提供"

    value = safe_text(marker.get("value"))
    palace = safe_text(marker.get("palace_name"))
    status = safe_text(marker.get("status"))

    return (
        f"{value}落{palace}宫"
        f"（{status}）"
    )


def update_shake_time(info):
    """每次点击摇爻都调用此函数。"""
    timezone = pytz.timezone(info["timezone"])
    now_aware = datetime.datetime.now(timezone)
    now_naive = now_aware.replace(tzinfo=None)

    offset = now_aware.utcoffset()

    if offset is None:
        raise ValueError("无法取得本次摇爻时间的 UTC 偏移。")

    line_number = len(
        st.session_state["yao_list"]
    ) + 1

    history = info.get("shake_history", [])

    history.append(
        {
            "line_number": line_number,
            "civil_time": now_aware.strftime(
                "%Y-%m-%d %H:%M:%S %Z"
            ),
        }
    )

    info["local_dt"] = now_naive.isoformat()
    info["local_dt_aware"] = now_aware.isoformat()
    info["utc_offset_hours"] = (
        offset.total_seconds() / 3600.0
    )
    info["last_shake_time"] = history[-1]["civil_time"]
    info["shake_history"] = history

    st.session_state["u_info"] = info


def calculate_context(info):
    """计算最终排盘时间、节气、四柱和奇门局数。"""
    local_dt = datetime.datetime.fromisoformat(
        info["local_dt"]
    )

    local_dt_aware = localize_datetime(
        info["timezone"],
        local_dt,
    )

    longitude = float(info["longitude"])
    latitude = float(info["latitude"])
    standard_meridian = float(
        info["standard_meridian"]
    )

    longitude_correction_minutes = (
        longitude - standard_meridian
    ) * 4.0

    local_mean_solar_dt = (
        local_dt
        + timedelta(
            minutes=longitude_correction_minutes
        )
    )

    calculate_eot = bool(
        info.get(
            "calculate_equation_of_time",
            False,
        )
    )

    if calculate_eot:
        equation_of_time_minutes = get_equation_of_time(
            local_dt
        )

        chart_dt = (
            local_mean_solar_dt
            + timedelta(
                minutes=equation_of_time_minutes
            )
        )

        chart_time_label = "均时差修正后的太阳时"
    else:
        equation_of_time_minutes = 0.0
        chart_dt = local_mean_solar_dt
        chart_time_label = "地方平太阳时"

    solar_engine = core_engine.PrecisionSolarEngine()

    (
        solar_longitude,
        term_name,
        dun_type,
        ju_map,
        yue_jiang,
    ) = solar_engine.get_solar_data(chart_dt)

    time_geo = TimeAndGeo()

    pillars = time_geo.get_pillars(
        chart_dt,
        solar_longitude=solar_longitude,
    )

    if term_name not in ju_map:
        raise ValueError(
            f"节气“{term_name}”没有对应奇门局数。"
        )

    ju = ju_map[term_name][
        pillars["yuan_idx"]
    ]

    return {
        "local_dt_aware": local_dt_aware,
        "longitude": longitude,
        "latitude": latitude,
        "standard_meridian": standard_meridian,
        "longitude_correction_minutes": (
            longitude_correction_minutes
        ),
        "local_mean_solar_dt": local_mean_solar_dt,
        "calculate_eot": calculate_eot,
        "equation_of_time_minutes": (
            equation_of_time_minutes
        ),
        "chart_dt": chart_dt,
        "chart_time_label": chart_time_label,
        "solar_longitude": solar_longitude,
        "term_name": term_name,
        "dun_type": dun_type,
        "yue_jiang": yue_jiang,
        "pillars": pillars,
        "ju": ju,
    }


def get_ziwei_data(info):
    """根据出生信息排紫微本命盘（辅助参考）。"""
    ziwei = ZiWeiEngine()

    return ziwei.run_natal(
        birth_date=info.get("birth_date"),
        birth_time=info.get("birth_time"),
        birth_place={
            "name": info.get("birth_place_name"),
            "longitude": info.get("birth_longitude"),
            "latitude": info.get("birth_latitude"),
        },
        gender=info.get("birth_gender"),
        timezone=info.get("birth_timezone"),
        leap_month_rule=info.get("leap_month_rule"),
        user_lunar_month=info.get("user_lunar_month"),
        target_year=info.get("target_year"),
    )


st.markdown(
    """
    <style>
    .status-bar {
        padding: 12px;
        background: #111;
        border: 1px dashed #444;
        border-radius: 6px;
        color: #00CC96;
        font-family: monospace;
        line-height: 1.75;
        margin-bottom: 18px;
    }

    .gua-line {
        font-size: 24px;
        font-family: monospace;
        font-weight: bold;
        margin: 5px 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🧿 赛博玄学 V36.2")

if "yao_list" not in st.session_state:
    st.session_state["yao_list"] = []

if "u_info" not in st.session_state:
    st.session_state["u_info"] = {}

if "geocoded_location" not in st.session_state:
    st.session_state["geocoded_location"] = None


# =========================================================
# 输入区域
# =========================================================

with st.sidebar:
    st.header("时空信息")

    st.caption(
        "六爻、奇门为主盘；紫微、大六壬为辅助参考。"
    )

    location_mode = st.radio(
        "地点输入方式",
        [
            "明确选择城市",
            "输入地址自动获取",
            "精确输入经纬度",
        ],
    )

    location_valid = True
    location_provider = "内置城市数据"
    coordinate_system = "WGS-84"
    address_text = ""

    if location_mode == "明确选择城市":
        selected_city = st.selectbox(
            "选择城市",
            list(CITY_DATA.keys()),
        )

        city_data = get_city_data(selected_city)

        city_name = selected_city
        longitude = float(city_data["longitude"])
        latitude = float(city_data["latitude"])
        timezone_name = city_data["timezone"]
        standard_meridian = float(
            city_data["standard_meridian"]
        )

        st.info(
            f"城市：{city_name}\n\n"
            f"经度：{longitude:.6f}°\n\n"
            f"纬度：{latitude:.6f}°\n\n"
            f"时区：{timezone_name}"
        )

    elif location_mode == "输入地址自动获取":
        address_input = st.text_input(
            "详细地址",
            placeholder="例如：黑龙江省佳木斯市向阳区",
        )

        city_hint = st.text_input(
            "城市提示，可选",
            placeholder="例如：佳木斯",
        )

        if st.button("获取经纬度"):
            if not address_input.strip():
                st.warning("请输入详细地址。")
            else:
                with st.spinner("正在解析地址..."):
                    result = geocode_address(
                        address=address_input,
                        city=city_hint,
                        use_nominatim_fallback=True,
                    )

                st.session_state[
                    "geocoded_location"
                ] = result

                if result is None:
                    st.error(
                        "地址无法识别，请补充省、市、区、街道，"
                        "或改用精确经纬度。"
                    )

        location_result = st.session_state.get(
            "geocoded_location"
        )

        if location_result is None:
            location_valid = False
            city_name = ""
            longitude = 0.0
            latitude = 0.0
            timezone_name = ""
            standard_meridian = 0.0

            st.warning(
                "尚未取得有效地点，不能锁定排盘。"
            )
        else:
            city_name = location_result["address"]
            address_text = location_result["address"]
            longitude = float(
                location_result["longitude"]
            )
            latitude = float(
                location_result["latitude"]
            )

            coordinate_system = location_result.get(
                "coordinate_system",
                "未知",
            )

            location_provider = location_result.get(
                "provider",
                "未知服务",
            )

            timezone_finder = TimezoneFinder()

            timezone_name = timezone_finder.timezone_at(
                lng=longitude,
                lat=latitude,
            )

            if not timezone_name:
                location_valid = False
                standard_meridian = 0.0

                st.error(
                    "已取得坐标，但无法识别时区。"
                )
            else:
                now_local = datetime.datetime.now(
                    pytz.timezone(timezone_name)
                )

                standard_meridian = get_standard_meridian(
                    timezone_name,
                    now_local,
                )

            st.info(
                f"地点：{city_name}\n\n"
                f"经度：{longitude:.6f}°\n\n"
                f"纬度：{latitude:.6f}°\n\n"
                f"坐标系：{coordinate_system}\n\n"
                f"时区：{timezone_name or '未知'}"
            )

            confirmed = st.checkbox(
                "我已核对地点、经纬度和时区",
                value=False,
            )

            if not confirmed:
                location_valid = False

    else:
        longitude = st.number_input(
            "经度 Longitude",
            min_value=-180.0,
            max_value=180.0,
            value=120.000000,
            format="%.6f",
        )

        latitude = st.number_input(
            "纬度 Latitude",
            min_value=-90.0,
            max_value=90.0,
            value=30.000000,
            format="%.6f",
        )

        city_name = "未提供地址，仅使用手动坐标"
        location_provider = "用户手动输入"
        coordinate_system = "用户未声明坐标系"

        try:
            validate_coordinates(
                longitude,
                latitude,
            )
        except ValueError as exc:
            location_valid = False
            st.error(str(exc))

        timezone_finder = TimezoneFinder()

        timezone_name = timezone_finder.timezone_at(
            lng=longitude,
            lat=latitude,
        )

        if not timezone_name:
            location_valid = False
            standard_meridian = 0.0

            st.error(
                "无法根据经纬度识别时区，已阻止排盘。"
            )
        else:
            now_local = datetime.datetime.now(
                pytz.timezone(timezone_name)
            )

            standard_meridian = get_standard_meridian(
                timezone_name,
                now_local,
            )

        st.info(
            f"地点：{city_name}\n\n"
            f"经度：{longitude:.6f}°\n\n"
            f"纬度：{latitude:.6f}°\n\n"
            f"时区：{timezone_name or '未知'}"
        )

    st.divider()

    calculate_eot = st.checkbox(
        "计算均时差",
        value=False,
    )

    if timezone_name:
        local_now = datetime.datetime.now(
            pytz.timezone(timezone_name)
        )
    else:
        local_now = datetime.datetime.now(pytz.UTC)

    st.divider()

    city_keys = list(CITY_DATA.keys())

    if location_mode == "明确选择城市" and city_name in city_keys:
        default_birth_city = city_name
    else:
        default_birth_city = city_keys[0]

    with st.form("entry_form"):
        initial_date = st.date_input(
            "初始当地民用日期",
            value=local_now.date(),
        )

        initial_time = st.time_input(
            "初始当地民用时间",
            value=local_now.time().replace(
                microsecond=0
            ),
        )

        user_name = st.text_input("求测人")
        question = st.text_input("问事")

        st.markdown("---")
        st.markdown("### 出生信息（必填）")
        st.caption(
            "出生信息同时用于：奇门年命、紫微本命盘。"
        )

        birth_date_input = st.date_input(
            "出生日期",
            value=datetime.date(1990, 1, 1),
        )

        birth_time_input = st.time_input(
            "出生时间",
            value=datetime.time(12, 0),
        )

              birth_location_mode = st.radio(
            "出生地点输入方式",
            ["选择城市", "手动输入经纬度"],
            horizontal=True,
        )

        if birth_location_mode == "选择城市":
            birth_city = st.selectbox(
                "出生城市",
                city_keys,
                index=city_keys.index(default_birth_city),
            )

            birth_city_data = get_city_data(birth_city)

            birth_place_name = birth_city
            birth_longitude = float(
                birth_city_data["longitude"]
            )
            birth_latitude = float(
                birth_city_data["latitude"]
            )
            birth_timezone = birth_city_data["timezone"]

            st.caption(
                f"{birth_city}：经度 {birth_longitude:.6f}°，"
                f"纬度 {birth_latitude:.6f}°，"
                f"时区 {birth_timezone}"
            )

        else:
            birth_place_name = st.text_input(
                "出生地名称，可选",
                value="",
                placeholder="例如：黑龙江省某县某乡",
            )

            birth_longitude = st.number_input(
                "出生地经度",
                min_value=-180.0,
                max_value=180.0,
                value=float(longitude),
                format="%.6f",
            )

            birth_latitude = st.number_input(
                "出生地纬度",
                min_value=-90.0,
                max_value=90.0,
                value=float(latitude),
                format="%.6f",
            )

            birth_timezone = ""

            try:
                validate_coordinates(
                    birth_longitude,
                    birth_latitude,
                )
            except ValueError as exc:
                birth_timezone = ""
                st.error(str(exc))
            else:
                birth_tz_finder = TimezoneFinder()

                birth_timezone = (
                    birth_tz_finder.timezone_at(
                        lng=birth_longitude,
                        lat=birth_latitude,
                    )
                )

                if not birth_timezone:
                    st.error(
                        "无法根据出生地经纬度识别时区，"
                        "请核对坐标，或改选城市。"
                    )
                else:
                    st.caption(
                        f"出生地："
                        f"{birth_place_name or '手动坐标'}　"
                        f"经度 {birth_longitude:.6f}°　"
                        f"纬度 {birth_latitude:.6f}°　"
                        f"时区 {birth_timezone}"
                    )

            if not birth_place_name.strip():
                birth_place_name = "手动经纬度地点"

        birth_gender = st.radio(
            "性别",
            ["男", "女"],
            horizontal=True,
        )

        leap_month_rule = st.selectbox(
            "闰月处理规则",
            [
                "按本月",
                "按下月",
                "用户指定",
                "流派默认",
            ],
        )

        if leap_month_rule == "用户指定":
            user_lunar_month = st.number_input(
                "用户指定排盘农历月",
                min_value=1,
                max_value=12,
                value=1,
            )
        else:
            user_lunar_month = None

        target_year = st.number_input(
            "目标流年，可选",
            min_value=1900,
            max_value=2200,
            value=local_now.year,
        )

        year_ming = year_to_zhi(
            birth_date_input.year
        )

        st.caption(
            f"出生年 {birth_date_input.year} 年，"
            f"奇门年命自动换算为：{year_ming}"
        )

        submitted = st.form_submit_button(
            "锁定地点并开始起卦",
            type="primary",
        )

        if submitted:
            if not location_valid:
                st.error(
                    "地点无效或尚未确认，已阻止排盘。"
                )

            elif not user_name.strip():
                st.warning("请填写求测人。")

            elif not question.strip():
                st.warning("请填写问事。")

            else:
                initial_dt = datetime.datetime.combine(
                    initial_date,
                    initial_time,
                )

                try:
                    initial_aware = localize_datetime(
                        timezone_name,
                        initial_dt,
                    )
                except ValueError as exc:
                    st.error(str(exc))
                    st.stop()

                utc_offset = initial_aware.utcoffset()

                if utc_offset is None:
                    st.error("无法取得当地 UTC 偏移。")
                    st.stop()

                st.session_state["u_info"] = {
                    "name": user_name.strip(),
                    "ask": question.strip(),
                    "city": city_name,
                    "address": address_text,
                    "longitude": float(longitude),
                    "latitude": float(latitude),
                    "timezone": timezone_name,
                    "coordinate_system": coordinate_system,
                    "location_provider": location_provider,
                    "standard_meridian": float(
                        standard_meridian
                    ),
                    "utc_offset_hours": (
                        utc_offset.total_seconds() / 3600.0
                    ),
                    "local_dt": initial_dt.isoformat(),
                    "local_dt_aware": initial_aware.isoformat(),
                    "calculate_equation_of_time": (
                        calculate_eot
                    ),
                    "shake_history": [],
                    "last_shake_time": None,
                    "year_ming": year_ming,
                    "birth_year": birth_date_input.year,
                    "birth_date": birth_date_input,
                    "birth_time": birth_time_input,
                    "birth_place_name": birth_place_name,
                    "birth_longitude": birth_longitude,
                    "birth_latitude": birth_latitude,
                    "birth_timezone": birth_timezone,
                    "birth_gender": birth_gender,
                    "leap_month_rule": leap_month_rule,
                    "user_lunar_month": user_lunar_month,
                    "target_year": target_year,
                }

                st.session_state["yao_list"] = []

                st.rerun()


if not st.session_state["u_info"]:
    st.info(
        "请在左侧输入地点和问事，然后锁定后开始起卦。"
    )
    st.stop()


info = st.session_state["u_info"]
yao_list = st.session_state["yao_list"]


# =========================================================
# 摇爻阶段
# =========================================================

if len(yao_list) < 6:
    try:
        current_context = calculate_context(info)
    except Exception as exc:
        st.error(f"无法计算当前时间：{exc}")
        st.stop()

    count = len(yao_list)

    st.subheader(
        f"六爻起卦：请摇第 {count + 1} 爻"
    )

    st.caption(
        "每次点击都会使用点击当刻重新记录当地民用时间。"
        "第六爻摇完后，最终盘使用第六次点击时间。"
    )

    st.info(
        f"当前时间快照："
        f"{current_context['local_dt_aware'].strftime('%Y-%m-%d %H:%M:%S %Z')}\n\n"
        f"当前四柱："
        f"{current_context['pillars']['year']} "
        f"{current_context['pillars']['month']} "
        f"{current_context['pillars']['day']} "
        f"{current_context['pillars']['hour']}\n\n"
        f"当前最终时间："
        f"{current_context['chart_dt'].strftime('%Y-%m-%d %H:%M:%S')}"
        f"（{current_context['chart_time_label']}）"
    )

    if info.get("shake_history"):
        st.caption("已记录摇爻时刻：")

        for record in info["shake_history"]:
            st.write(
                f"第 {record['line_number']} 爻："
                f"{record['civil_time']}"
            )

    st.write("当前卦象，初爻在下：")

    for index in range(count - 1, -1, -1):
        value = yao_list[index]

        line = (
            "■■■■■"
            if value in [7, 9]
            else "■■　■■"
        )

        label_map = {
            6: "老阴",
            7: "少阳",
            8: "少阴",
            9: "老阳",
        }

        color = (
            "#FF4B4B"
            if value in [6, 9]
            else "#E0E0E0"
        )

        st.markdown(
            f"<div class='gua-line' "
            f"style='color:{color}'>"
            f"{line}（{label_map[value]}）"
            f"</div>",
            unsafe_allow_html=True,
        )

    if st.button(
        "摇出此爻并刷新排盘时间",
        type="primary",
        use_container_width=True,
    ):
        try:
            update_shake_time(info)
        except ValueError as exc:
            st.error(str(exc))
            st.stop()

        st.session_state["yao_list"].append(
            random.choice(
                [6, 7, 7, 7, 8, 8, 8, 9]
            )
        )

        st.rerun()

    st.stop()


# =========================================================
# 最终时间、四柱与四个模块
# =========================================================

info = st.session_state["u_info"]
yao_list = st.session_state["yao_list"]

try:
    context = calculate_context(info)
except Exception as exc:
    st.error(f"无法计算最终排盘时间：{exc}")
    st.stop()

local_dt_aware = context["local_dt_aware"]
longitude = context["longitude"]
latitude = context["latitude"]
standard_meridian = context["standard_meridian"]
longitude_correction_minutes = (
    context["longitude_correction_minutes"]
)
calculate_eot = context["calculate_eot"]
equation_of_time_minutes = (
    context["equation_of_time_minutes"]
)
chart_dt = context["chart_dt"]
chart_time_label = context["chart_time_label"]
solar_longitude = context["solar_longitude"]
term_name = context["term_name"]
dun_type = context["dun_type"]
yue_jiang = context["yue_jiang"]
pillars = context["pillars"]
ju = context["ju"]


qimen = core_engine.QimenEngine()

qimen_data = qimen.run(
    ju=ju,
    is_yang=dun_type == "阳遁",
    xun=pillars["xun"],
    h_gan=pillars["h_gan"],
    h_zhi=pillars["h_zhi"],
    kw=pillars["kw"],
    day_gan=pillars["day_gan"],
    year_gan=pillars["year"][0],
    year_ming=info.get("year_ming"),
    user_mapping={
        "本人": {
            "rule": "日干",
            "requires_confirmation": False,
        },
        "感情对象": {
            "rule": "乙/六合",
            "requires_confirmation": True,
        },
        "工作关系": {
            "rule": "开门",
            "requires_confirmation": True,
        },
    },
    return_details=True,
)

qimen_markers = qimen_data["markers"]

liuyao = core_engine.LiuYaoEngine()

gua_data = liuyao.process(
    codes=yao_list,
    month_branch=pillars["month"][-1],
    day_branch=pillars["day_zhi"],
    day_gan=pillars["day_gan"],
    xun_kong=pillars["kw"],
)

ziwei_data = get_ziwei_data(info)

liuren = DaLiuRenEngine()

liuren_data = liuren.run(
    yue_jiang=yue_jiang,
    hour_zhi=pillars["h_zhi"],
    day_gan=pillars["day_gan"],
    day_zhi=pillars["day_zhi"],
    xun_shou=pillars["xun"],
    xun_kong=pillars["kw"],
)


# =========================================================
# 时空总览
# =========================================================

st.success("六爻完成，最终盘使用第六次摇爻时刻。")

eot_text = (
    f"已计算，{equation_of_time_minutes:+.2f} 分钟"
    if calculate_eot
    else "未计算"
)

st.markdown(
    f"""
    <div class="status-bar">
    地点：{info['city']}<br>
    经度：{longitude:.6f}°　纬度：{latitude:.6f}°<br>
    坐标系：{info['coordinate_system']}　数据来源：{info['location_provider']}<br>
    时区：{info['timezone']}　UTC偏移：UTC{info['utc_offset_hours']:+.1f}<br>
    最后摇爻时刻：{safe_text(info.get('last_shake_time'))}<br>
    经度修正：{longitude_correction_minutes:+.2f} 分钟<br>
    均时差：{eot_text}<br>
    最终排盘时间：{chart_dt.strftime('%Y-%m-%d %H:%M:%S')}
    （{chart_time_label}）<br>
    太阳黄经：{solar_longitude:.4f}°　节气：{term_name}
    </div>
    """,
    unsafe_allow_html=True,
)

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    chart_time_label,
    chart_dt.strftime("%m-%d %H:%M:%S"),
    "早子时"
    if pillars["is_early_zi"]
    else None,
)

c2.metric(
    "四柱",
    (
        f"{pillars['year']} "
        f"{pillars['month']} "
        f"{pillars['day']} "
        f"{pillars['hour']}"
    ),
)

c3.metric(
    "奇门",
    f"{dun_type}{ju}局",
    f"值符：{qimen_markers['zhi_fu']['value']}",
)

c4.metric(
    "大六壬",
    safe_text(
        liuren_data["san_chuan_rule"]
    ),
    "辅助参考",
)

st.write(f"### 问测：{info['ask']}")


# =========================================================
# 六爻显示（主盘）
# =========================================================

st.divider()
st.subheader("六爻（主盘）")

st.write(
    f"本卦：**{gua_data['ben']}**　"
    f"变卦：**{gua_data['bian']}**　"
    f"动爻：**{safe_text(gua_data['moves'])}**"
)

st.caption(
    f"卦宫：{safe_text(gua_data['palace'])}　"
    f"世爻：第{safe_text(gua_data['shi_position'])}爻　"
    f"应爻：第{safe_text(gua_data['ying_position'])}爻　"
    f"旬空：{safe_text(gua_data['xun_kong'])}"
)

liuyao_rows = []

for line_data in gua_data["lines"]:
    strength = line_data.get("strength", {})

    if isinstance(strength, dict):
        strength = strength.get("label", "未计算")

    hidden_text = []

    for hidden in line_data.get(
        "hidden_lines",
        [],
    ):
        hidden_text.append(
            f"{hidden.get('relative', '')}"
            f"{hidden.get('najia', '')}"
        )

    liuyao_rows.append(
        {
            "爻位": line_data["name"],
            "爻值": line_data["value"],
            "阴阳": line_data["yin_yang"],
            "动爻": "是" if line_data["moving"] else "否",
            "变后": line_data["changed_yin_yang"],
            "纳甲": line_data["najia"],
            "六亲": line_data["relative"],
            "六神": line_data["six_god"],
            "世应": line_data["role"],
            "旬空": "是" if line_data["void"] else "否",
            "旺衰": strength,
            "伏神": "；".join(hidden_text) or "无",
        }
    )

st.dataframe(
    liuyao_rows,
    use_container_width=True,
    hide_index=True,
)

if gua_data["warnings"]:
    st.warning("六爻警告")
    for item in gua_data["warnings"]:
        st.write(f"- {item}")


# =========================================================
# 奇门显示（主盘）
# =========================================================

st.divider()
st.subheader("奇门遁甲（主盘）")

st.caption(
    f"流派/方法：{qimen_data['school']} | "
    f"{qimen_data['method']}"
)

st.write(
    f"遁法：{qimen_data['yin_yang']}　"
    f"局数：{qimen_data['ju_number']}　"
    f"旬首：{qimen_data['xun_shou']}　"
    f"旬空：{safe_text(qimen_data['void_branches'])}"
)

if info.get("birth_year"):
    st.caption(
        f"年命：出生年 {info['birth_year']}，"
        f"自动换算为地支 {safe_text(info.get('year_ming'))}"
    )

marker_labels = [
    ("日干", "day_gan"),
    ("年干", "year_gan"),
    ("年命", "year_ming"),
    ("乙", "yi"),
    ("六合", "liu_he"),
    ("开门", "open_door"),
    ("生门", "life_door"),
    ("值符", "zhi_fu"),
    ("值使", "zhi_shi"),
]

marker_rows = []

for label, key in marker_labels:
    marker = qimen_markers[key]

    marker_rows.append(
        {
            "取用符号": label,
            "对象值": marker["value"],
            "落宫": marker["palace_name"],
            "状态": marker["status"],
        }
    )

st.dataframe(
    marker_rows,
    use_container_width=True,
    hide_index=True,
)

qimen_rows = []

for palace_name, palace_data in (
    qimen_data["palaces"].items()
):
    qimen_rows.append(
        {
            "宫位": palace_name,
            "宫号": palace_data["palace_number"],
            "地盘干": palace_data["earth_stem"],
            "天盘干": palace_data["heaven_stem"],
            "九星": palace_data["star"],
            "八门": palace_data["door"],
            "八神": palace_data["deity"],
            "空亡": "是" if palace_data["void"] else "否",
        }
    )

st.dataframe(
    qimen_rows,
    use_container_width=True,
    hide_index=True,
)

st.caption(
    "本次取用规则：本人候选取日干；感情对象候选取乙或六合；"
    "工作关系候选取开门。现实对象必须由用户确认，"
    "不会自动等同于具体人物、城市或关系。"
)

if qimen_data["warnings"]:
    st.warning("奇门警告")
    for item in qimen_data["warnings"]:
        st.write(f"- {item}")


# =========================================================
# 紫微显示（辅助，本命盘）
# =========================================================

st.divider()
st.subheader("紫微斗数（辅助参考）")

st.caption(
    f"模式：{ziwei_data.get('mode')}　"
    f"状态：{ziwei_data.get('status')}"
)

st.warning(
    "紫微在此程序中作为辅助参考，不单独作结论。"
    "本命盘为简化版，未做真太阳时校正。"
)

if ziwei_data.get("status") == "invalid":
    st.error(safe_text(ziwei_data.get("warnings")))
else:
    st.write(
        f"农历：{safe_text(ziwei_data.get('lunar_month'))}月 "
        f"{safe_text(ziwei_data.get('lunar_day'))}日　"
        f"五行局：{safe_text(ziwei_data.get('wuxing_ju'))}"
    )

    ming = safe_text(ziwei_data.get("ming_gong_branch"))
    shen = safe_text(ziwei_data.get("shen_gong_branch"))

    if ming != "未提供" or shen != "未提供":
        st.write(f"命宫：{ming}　身宫：{shen}")

    spouse_palace = ziwei_data.get("spouse_palace")

    if spouse_palace:
        spouse_stars = safe_text(
            spouse_palace.get(
                "all_stars",
                spouse_palace.get("main_stars"),
            ),
            "空宫",
        )

        st.write(
            f"夫妻宫：{spouse_palace.get('branch')}　"
            f"星曜：{spouse_stars}"
        )

    twelve_palaces = ziwei_data.get(
        "twelve_palaces_by_name"
    ) or {}

    if twelve_palaces:
        ziwei_rows = []

        for palace_name, palace_data in twelve_palaces.items():
            stars = palace_data.get(
                "all_stars",
                palace_data.get("main_stars", []),
            )

            ziwei_rows.append(
                {
                    "宫名": palace_name,
                    "地支": palace_data.get("branch"),
                    "星曜": safe_text(stars, "空宫"),
                    "命宫": (
                        "是"
                        if palace_data.get("is_ming_gong")
                        else ""
                    ),
                    "身宫": (
                        "是"
                        if palace_data.get("is_shen_gong")
                        else ""
                    ),
                }
            )

        st.dataframe(
            ziwei_rows,
            use_container_width=True,
            hide_index=True,
        )

    four_transformations = ziwei_data.get(
        "four_transformations",
        {},
    ) or {}

    transformation_items = four_transformations.get(
        "items",
        {},
    ) or {}

    if transformation_items:
        transformation_rows = []

        for name, item in transformation_items.items():
            transformation_rows.append(
                {
                    "四化": name,
                    "星曜": item.get("star"),
                    "宫位": item.get("palace_name"),
                    "地支": item.get("branch"),
                    "状态": item.get("status"),
                }
            )

        st.dataframe(
            transformation_rows,
            use_container_width=True,
            hide_index=True,
        )

    decadal_limits = ziwei_data.get(
        "decadal_limits",
        {},
    ) or {}

    decadal_palaces = decadal_limits.get(
        "palaces",
        [],
    ) or []

    if decadal_palaces:
        st.caption(
            f"大限方向：{safe_text(decadal_limits.get('direction'))}　"
            f"起限：{safe_text(decadal_limits.get('start_age'))}岁"
        )

        decadal_rows = []

        for palace_data in decadal_palaces:
            decadal_rows.append(
                {
                    "宫位": palace_data.get("palace_name"),
                    "地支": palace_data.get("branch"),
                    "起岁": palace_data.get("start_age"),
                    "止岁": palace_data.get("end_age"),
                }
            )

        st.dataframe(
            decadal_rows,
            use_container_width=True,
            hide_index=True,
        )

    annual_data = ziwei_data.get(
        "annual_data",
        {},
    ) or {}

    annual_palace = annual_data.get(
        "annual_palace",
        {},
    ) or {}

    if annual_palace.get("branch"):
        st.write(
            f"流年 {safe_text(annual_data.get('target_year'))}："
            f"命宫在 {annual_palace.get('branch')}　"
            f"（{safe_text(annual_palace.get('palace_name'))}）"
        )

        liu_trans = annual_data.get(
            "transformations",
            {},
        ) or {}

        liu_items = liu_trans.get("items", {}) or {}

        if liu_items:
            liu_rows = []

            for name, item in liu_items.items():
                liu_rows.append(
                    {
                        "流年四化": name,
                        "星曜": item.get("star"),
                        "宫位": item.get("palace_name"),
                        "地支": item.get("branch"),
                        "状态": item.get("status"),
                    }
                )

            st.dataframe(
                liu_rows,
                use_container_width=True,
                hide_index=True,
            )

if ziwei_data.get("warnings"):
    st.warning("紫微警告")
    for item in ziwei_data["warnings"]:
        st.write(f"- {item}")


# =========================================================
# 大六壬显示（辅助）
# =========================================================

st.divider()
st.subheader("大六壬（辅助参考）")

st.caption(
    f"流派/方法：{liuren_data['school']} | "
    f"{liuren_data['method']}"
)

st.warning(
    "大六壬在此程序中仅作辅助参考。"
    "三传受九宗门实现范围限制，"
    "不单独作为结论依据。"
)

course_type = liuren_data["course_type"]
three_transmissions = liuren_data[
    "three_transmissions"
]

st.write(
    f"月将：{liuren_data['yue_jiang']}　"
    f"日干寄宫：{liuren_data['ji_gong']}　"
    f"课体：{course_type['name']}　"
    f"三传规则：{three_transmissions['rule']}　"
    f"三传状态：{three_transmissions['status']}"
)

transmission_rows = []

for item in liuren_data["san_chuan"]:
    transmission_rows.append(
        {
            "传位": item["pos"],
            "地支": item["zhi"],
            "天将": item["jiang"],
            "六亲": item["six_relation"],
            "状态": item["status"],
        }
    )

st.dataframe(
    transmission_rows,
    use_container_width=True,
    hide_index=True,
)

lesson_rows = []

for lesson in liuren_data["four_lessons"]:
    lesson_rows.append(
        {
            "课": lesson["name"],
            "上神": lesson["top"],
            "下神": lesson["bottom"],
            "关系": lesson["relation"],
        }
    )

st.dataframe(
    lesson_rows,
    use_container_width=True,
    hide_index=True,
)

with st.expander("查看天地盘与三传推导日志"):
    st.write("地盘支 -> 天盘支：")

    st.write(
        "；".join(
            f"{earth}上临{heaven}"
            for earth, heaven in (
                liuren_data[
                    "heaven_plate_by_earth"
                ].items()
            )
        )
    )

    st.write("三传推导：")

    for step in three_transmissions[
        "derivation_steps"
    ]:
        st.write(f"- {step}")

if liuren_data["warnings"]:
    st.warning("大六壬警告")
    for item in liuren_data["warnings"]:
        st.write(f"- {item}")


# =========================================================
# AI 提示词：精简版
# =========================================================

def _strength_label(line_data):
    strength = line_data.get("strength", {})

    if isinstance(strength, dict):
        return strength.get("label", "未计算")

    return safe_text(strength, "未计算")


liuyao_lines = []

for line_data in reversed(gua_data["lines"]):
    move = "动" if line_data["moving"] else "静"
    void = "空" if line_data["void"] else ""
    role = (
        line_data["role"]
        if line_data["role"] != "普通"
        else ""
    )

    hidden_parts = []

    for hidden in line_data.get("hidden_lines", []):
        hidden_parts.append(
            f"{hidden.get('relative', '')}"
            f"{hidden.get('najia', '')}"
        )

    hidden_text = (
        f"伏{'/'.join(hidden_parts)}"
        if hidden_parts
        else ""
    )

    liuyao_lines.append(
        f"{line_data['name']} {line_data['yin_yang']}{move} "
        f"{line_data['najia']} {line_data['six_god']} "
        f"{line_data['relative']} {role}{void} "
        f"{_strength_label(line_data)}{hidden_text}"
    )


marker_short = []

for label, key in marker_labels:
    marker = qimen_markers[key]
    value = safe_text(marker.get("value"), "未取")
    palace = safe_text(
        marker.get("palace_name"),
        "未落宫",
    )

    if marker.get("status") == "未实现":
        marker_short.append(f"{label}未实现")
    else:
        marker_short.append(f"{label}{value}落{palace}宫")


qimen_gong = []

for palace_name, palace_data in qimen_data["palaces"].items():
    qimen_gong.append(
        f"{palace_name}："
        f"天{palace_data['heaven_stem']}/"
        f"地{palace_data['earth_stem']} "
        f"{palace_data['star']} "
        f"{palace_data['door']} "
        f"{palace_data['deity']} "
        f"{'空' if palace_data['void'] else '不空'}"
    )


def _chuan(item):
    return (
        f"{safe_text(item.get('zhi'), '?')}"
        f"（{safe_text(item.get('jiang'), '?')}/"
        f"{safe_text(item.get('six_relation'), '?')}）"
    )


liuren_san_chuan = (
    f"初{_chuan(liuren_data['san_chuan'][0])} "
    f"中{_chuan(liuren_data['san_chuan'][1])} "
    f"末{_chuan(liuren_data['san_chuan'][2])}"
)

liuren_sike = "，".join(
    f"{lesson['name']}"
    f"{lesson['top']}上{lesson['bottom']}下"
    f"（{lesson['relation']}）"
    for lesson in liuren_data["four_lessons"]
)


ziwei_parts = [
    f"农历{safe_text(ziwei_data.get('lunar_month'))}月"
    f"{safe_text(ziwei_data.get('lunar_day'))}日，"
    f"五行局{safe_text(ziwei_data.get('wuxing_ju'))}"
]

ming = safe_text(ziwei_data.get("ming_gong_branch"), "未算")
shen = safe_text(ziwei_data.get("shen_gong_branch"), "未算")
ziwei_parts.append(f"命宫{ming}，身宫{shen}")

twelve_palaces = ziwei_data.get(
    "twelve_palaces_by_name"
) or {}

if twelve_palaces:
    palace_str = "；".join(
        f"{name}在{pa.get('branch')}"
        f"（{safe_text(pa.get('all_stars', pa.get('main_stars', [])), '空')}）"
        for name, pa in twelve_palaces.items()
    )

    ziwei_parts.append("十二宫：" + palace_str)

four_transformations = ziwei_data.get(
    "four_transformations",
    {},
) or {}

transformation_items = four_transformations.get(
    "items",
    {},
) or {}

if transformation_items:
    ft_str = "，".join(
        f"{name}化{item.get('star')}"
        f"在{safe_text(item.get('palace_name'), '未定位')}"
        for name, item in transformation_items.items()
    )

    ziwei_parts.append("生年四化：" + ft_str)

decadal_limits = ziwei_data.get(
    "decadal_limits",
    {},
) or {}

if decadal_limits.get("direction"):
    ziwei_parts.append(
        f"大限{decadal_limits.get('direction')}，"
        f"起限{safe_text(decadal_limits.get('start_age'))}岁"
    )

annual_data = ziwei_data.get(
    "annual_data",
    {},
) or {}

annual_palace = annual_data.get(
    "annual_palace",
    {},
) or {}

if annual_palace.get("branch"):
    ziwei_parts.append(
        f"流年{annual_data.get('target_year')}"
        f"命宫在{annual_palace.get('branch')}"
    )

ziwei_summary = "；".join(ziwei_parts)


prompt_lines = [
    "你是玄学排盘解读助手。以下数据已由程序计算完成，请据此回答问事。",
    "主盘：六爻、奇门；辅助：紫微、大六壬（仅旁证，不单独作结论）。",
    "",
    "【基本信息】",
    f"求测人：{info['name']}；问事：{info['ask']}",
    f"地点：{info['city']}；时区：{info['timezone']}",
    (
        f"排盘时间：{chart_dt.strftime('%Y-%m-%d %H:%M:%S')}"
        f"（{chart_time_label}）"
    ),
    (
        f"四柱：{pillars['year']} {pillars['month']} "
        f"{pillars['day']} {pillars['hour']}；"
        f"节气：{term_name}；旬首：{pillars['xun']}；"
        f"旬空：{pillars['kw']}"
    ),
    "",
    "【主盘一：六爻】",
    (
        f"本卦{gua_data['ben']}，变卦{gua_data['bian']}，"
        f"动爻{safe_text(gua_data['moves'])}，"
        f"世第{safe_text(gua_data['shi_position'])}爻，"
        f"应第{safe_text(gua_data['ying_position'])}爻"
    ),
    *liuyao_lines,
    "",
    "【主盘二：奇门】",
    f"{qimen_data['yin_yang']}{qimen_data['ju_number']}局，"
    f"旬首{qimen_data['xun_shou']}，"
    f"旬空{safe_text(qimen_data['void_branches'])}",
    "；".join(marker_short),
    "；".join(qimen_gong),
    "",
    "【辅助：大六壬】",
    (
        f"月将{liuren_data['yue_jiang']}，"
        f"课体{course_type['name']}，三传{liuren_san_chuan}"
    ),
    f"四课：{liuren_sike}",
    "",
    "【辅助：紫微】",
    ziwei_summary,
    "",
    "【规则】",
    (
        "1. 以六爻为主判断，奇门印证；"
        "紫微、六壬仅旁证，冲突时分别说明，不强行统一。"
    ),
    (
        "2. 取用：本人=日干；感情候选=乙/六合；"
        "工作候选=开门；对象未明确时必须写“对象未确认”。"
    ),
    (
        "3. 输出四段：可由数据支持的内容；"
        "证据不足无法确认的内容；需要补充资料的内容；"
        "仅供参考的推测。"
    ),
    (
        "4. 不补造缺失数据，不把推测当事实，"
        "简化算法要注明，不编造日期、地点或人物。"
    ),
]

ai_prompt = "\n".join(prompt_lines)

st.divider()

st.text_area(
    "发送给 AI 的结构化排盘摘要",
    ai_prompt,
    height=760,
)

st.divider()

if st.button(
    "销毁当前存储并重置",
    type="primary",
):
    st.session_state.clear()
    st.rerun()
