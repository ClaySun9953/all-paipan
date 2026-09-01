# -*- coding: utf-8 -*-

"""
紫微斗数模块（完整替换版）。

模式：
1. auxiliary：问测时间辅助参考模式（兼容旧调用 run(dt)）。
2. natal：本命紫微盘模式。

本版本新增：
- 十四主星
- 辅星：文昌、文曲、左辅、右弼、禄存、擎羊、陀罗、
  天魁、天钺、天马、火星、铃星、地空、地劫
- 生年四化定位
- 大限起限岁数与每宫起止
- 流年命宫与流年四化（基础版）

仍未实现：
- 真太阳时校正
- 完整流月、流日、流时
- 南北派/飞星/三合等完整流派细分
"""

import datetime
from zoneinfo import ZoneInfo

from lunar_python import Solar


class ZiWeiEngine:
    """紫微斗数排盘引擎。"""

    ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]

    ZHI_YINYANG = {
        "子": "阳", "丑": "阴", "寅": "阳", "卯": "阴", "辰": "阳", "巳": "阴",
        "午": "阳", "未": "阴", "申": "阳", "酉": "阴", "戌": "阳", "亥": "阴",
    }
    GAN_YINYANG = {
        "甲": "阳", "乙": "阴", "丙": "阳", "丁": "阴", "戊": "阳",
        "己": "阴", "庚": "阳", "辛": "阴", "壬": "阳", "癸": "阴",
    }

    ZIWEI_STARS = {
        0: "紫微", 1: "天机", 3: "太阳", 4: "武曲", 5: "天同", 8: "廉贞",
    }
    TIANFU_STARS = {
        0: "天府", 1: "太阴", 2: "贪狼", 3: "巨门", 4: "天相",
        5: "天梁", 6: "七杀", 10: "破军",
    }

    PALACE_NAMES = [
        "命宫", "兄弟宫", "夫妻宫", "子女宫", "财帛宫", "疾厄宫",
        "迁移宫", "交友宫", "官禄宫", "田宅宫", "福德宫", "父母宫",
    ]

    FOUR_TRANSFORMATIONS = {
        "甲": {"禄": "廉贞", "权": "破军", "科": "武曲", "忌": "太阳"},
        "乙": {"禄": "天机", "权": "天梁", "科": "紫微", "忌": "太阴"},
        "丙": {"禄": "天同", "权": "天机", "科": "文昌", "忌": "廉贞"},
        "丁": {"禄": "太阴", "权": "天同", "科": "天机", "忌": "巨门"},
        "戊": {"禄": "贪狼", "权": "太阴", "科": "右弼", "忌": "天机"},
        "己": {"禄": "武曲", "权": "贪狼", "科": "天梁", "忌": "文曲"},
        "庚": {"禄": "太阳", "权": "武曲", "科": "太阴", "忌": "天同"},
        "辛": {"禄": "巨门", "权": "太阳", "科": "文曲", "忌": "文昌"},
        "壬": {"禄": "天梁", "权": "紫微", "科": "左辅", "忌": "武曲"},
        "癸": {"禄": "破军", "权": "巨门", "科": "太阴", "忌": "贪狼"},
    }

    LEAP_MONTH_RULES = {
        "按本月": "闰月仍按原农历月份排盘。",
        "按下月": "闰月按下一农历月份排盘。",
        "用户指定": "必须由调用方显式提供 user_lunar_month。",
        "流派默认": "采用本项目默认规则，当前默认值为按本月。",
    }
    DEFAULT_LEAP_MONTH_RULE = "按本月"

    # ---------- 辅星定位表 ----------
    WENCHANG_BY_GAN = {
        "甲": "巳", "乙": "午", "丙": "申", "丁": "酉", "戊": "申",
        "己": "酉", "庚": "亥", "辛": "子", "壬": "寅", "癸": "卯",
    }
    WENQU_BY_GAN = {
        "甲": "亥", "乙": "子", "丙": "寅", "丁": "卯", "戊": "寅",
        "己": "卯", "庚": "巳", "辛": "午", "壬": "申", "癸": "酉",
    }
    LUCUN_BY_GAN = {
        "甲": "寅", "乙": "卯", "丙": "巳", "丁": "午", "戊": "巳",
        "己": "午", "庚": "申", "辛": "酉", "壬": "亥", "癸": "子",
    }
    TIANKUI_BY_GAN = {
        "甲": "丑", "戊": "丑", "庚": "丑",
        "乙": "子", "己": "子",
        "丙": "亥", "丁": "亥",
        "壬": "卯", "癸": "卯",
        "辛": "午",
    }
    TIANYUE_BY_GAN = {
        "甲": "未", "戊": "未", "庚": "未",
        "乙": "申", "己": "申",
        "丙": "酉", "丁": "酉",
        "壬": "巳", "癸": "巳",
        "辛": "寅",
    }
    TIANMA_BY_ZHI = {
        "寅": "申", "午": "申", "戌": "申",
        "申": "寅", "子": "寅", "辰": "寅",
        "巳": "亥", "酉": "亥", "丑": "亥",
        "亥": "巳", "卯": "巳", "未": "巳",
    }
    HUOXING_START = {
        "寅": "丑", "午": "丑", "戌": "丑",
        "申": "寅", "子": "寅", "辰": "寅",
        "巳": "卯", "酉": "卯", "丑": "卯",
        "亥": "酉", "卯": "酉", "未": "酉",
    }
    LINGXING_START = {
        "寅": "卯", "午": "卯", "戌": "卯",
        "申": "戌", "子": "戌", "辰": "戌",
        "巳": "戌", "酉": "戌", "丑": "戌",
        "亥": "戌", "卯": "戌", "未": "戌",
    }

    def __init__(self):
        self._validate_static_data()

    def _validate_static_data(self):
        if len(self.ZHI) != 12 or len(self.GAN) != 10 or len(self.PALACE_NAMES) != 12:
            raise ValueError("紫微基础表配置错误。")

    def _normalize_datetime(self, dt):
        if not isinstance(dt, datetime.datetime):
            raise TypeError("时间参数必须是 datetime.datetime。")
        return dt.replace(tzinfo=None)

    def _normalize_gender(self, gender):
        if gender is None:
            return None
        gender = str(gender).strip()
        if gender in ["男", "男性", "male", "Male", "M"]:
            return "男"
        if gender in ["女", "女性", "female", "Female", "F"]:
            return "女"
        return None

    def _normalize_timezone(self, timezone_name):
        if timezone_name is None:
            return None
        timezone_name = str(timezone_name).strip()
        if not timezone_name:
            return None
        try:
            ZoneInfo(timezone_name)
        except Exception:
            return None
        return timezone_name

    def _normalize_birth_place(self, birth_place):
        if birth_place is None:
            return None
        if isinstance(birth_place, str):
            name = birth_place.strip()
            if not name:
                return None
            return {"name": name, "longitude": None, "latitude": None,
                    "status": "地点名称已提供，坐标未提供"}
        if not isinstance(birth_place, dict):
            return None
        name = str(birth_place.get("name") or birth_place.get("city")
                   or birth_place.get("address") or "").strip()
        try:
            longitude = float(birth_place.get("longitude")) if birth_place.get("longitude") is not None else None
            latitude = float(birth_place.get("latitude")) if birth_place.get("latitude") is not None else None
        except (TypeError, ValueError):
            return None
        if longitude is not None and not -180.0 <= longitude <= 180.0:
            return None
        if latitude is not None and not -90.0 <= latitude <= 90.0:
            return None
        if not name and longitude is None and latitude is None:
            return None
        return {
            "name": name or "手动经纬度地点",
            "longitude": longitude,
            "latitude": latitude,
            "status": "地点与坐标已提供" if (longitude is not None and latitude is not None)
            else "地点已提供，坐标未提供",
        }

    def _normalize_leap_month_rule(self, leap_month_rule):
        if leap_month_rule is None:
            return None
        leap_month_rule = str(leap_month_rule).strip()
        return leap_month_rule if leap_month_rule in self.LEAP_MONTH_RULES else None

    def _combine_birth_datetime(self, birth_date, birth_time):
        if isinstance(birth_date, datetime.datetime):
            return birth_date.replace(tzinfo=None)
        if not isinstance(birth_date, datetime.date) or not isinstance(birth_time, datetime.time):
            return None
        return datetime.datetime.combine(birth_date, birth_time)

    def _get_hour_zhi_index(self, dt):
        return ((dt.hour + 1) // 2) % 12

    def _get_lunar_raw_info(self, dt):
        dt = self._normalize_datetime(dt)
        solar = Solar.fromYmdHms(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
        lunar = solar.getLunar()
        raw_month = lunar.getMonth()
        is_leap_month = raw_month < 0
        return {
            "solar_datetime": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "lunar_year": lunar.getYear(),
            "lunar_month_raw": raw_month,
            "lunar_month_original": abs(raw_month),
            "lunar_day": lunar.getDay(),
            "is_leap_month": is_leap_month,
            "year_gan": lunar.getYearGan(),
            "year_zhi": lunar.getYearZhi(),
            "hour_zhi_index": self._get_hour_zhi_index(dt),
            "hour_zhi": self.ZHI[self._get_hour_zhi_index(dt)],
        }

    def _resolve_lunar_month(self, lunar_info, leap_month_rule, user_lunar_month=None):
        warnings = []
        original_month = lunar_info["lunar_month_original"]
        is_leap_month = lunar_info["is_leap_month"]
        if leap_month_rule == "流派默认":
            effective_rule = self.DEFAULT_LEAP_MONTH_RULE
            warnings.append("闰月处理选择“流派默认”，"
                            f"本项目当前默认采用“{effective_rule}”。")
        else:
            effective_rule = leap_month_rule

        if not is_leap_month:
            return {"original_month": original_month, "effective_month": original_month,
                    "is_leap_month": False, "requested_rule": leap_month_rule,
                    "effective_rule": effective_rule, "rule_description": "非闰月，直接使用原农历月份。",
                    "warnings": warnings}

        if effective_rule == "按本月":
            effective_month = original_month
            description = "闰月按原农历月份排盘。"
        elif effective_rule == "按下月":
            effective_month = original_month + 1
            if effective_month > 12:
                effective_month = 1
                warnings.append("闰腊月按下月处理后跨入正月。该规则存在流派差异，请用户确认。")
            description = "闰月按下一农历月份排盘。"
        elif effective_rule == "用户指定":
            try:
                effective_month = int(user_lunar_month)
            except (TypeError, ValueError):
                effective_month = None
            if effective_month not in range(1, 13):
                warnings.append("闰月规则为“用户指定”，但 user_lunar_month 不是 1 至 12。")
                return {"original_month": original_month, "effective_month": None,
                        "is_leap_month": True, "requested_rule": leap_month_rule,
                        "effective_rule": effective_rule,
                        "rule_description": "用户指定月份无效，未排本命盘。", "warnings": warnings}
            description = f"闰月按用户指定农历{effective_month}月排盘。"
        else:
            warnings.append("闰月规则无法识别。")
            return {"original_month": original_month, "effective_month": None,
                    "is_leap_month": is_leap_month, "requested_rule": leap_month_rule,
                    "effective_rule": None, "rule_description": "规则无效。", "warnings": warnings}
        return {"original_month": original_month, "effective_month": effective_month,
                "is_leap_month": True, "requested_rule": leap_month_rule,
                "effective_rule": effective_rule, "rule_description": description, "warnings": warnings}

    def get_lunar_info(self, dt, leap_month_rule="流派默认", user_lunar_month=None):
        leap_month_rule = self._normalize_leap_month_rule(leap_month_rule)
        if leap_month_rule is None:
            raise ValueError("闰月处理规则必须是：按本月、按下月、用户指定、流派默认之一。")
        lunar_info = self._get_lunar_raw_info(dt)
        leap_info = self._resolve_lunar_month(lunar_info, leap_month_rule, user_lunar_month)
        return {**lunar_info, "lunar_month": leap_info["effective_month"],
                "is_leap_corrected": lunar_info["is_leap_month"],
                "leap_month_handling": leap_info}

    def calc_palace_layout(self, lunar_month, hour_zhi_idx):
        if lunar_month not in range(1, 13):
            raise ValueError("农历月份必须在 1 至 12 之间。")
        if hour_zhi_idx not in range(12):
            raise ValueError("时支索引必须在 0 至 11 之间。")
        ming_idx = (2 + (lunar_month - 1) - hour_zhi_idx) % 12
        shen_idx = (2 + (lunar_month - 1) + hour_zhi_idx) % 12
        return ming_idx, shen_idx

    def _get_ming_gan_index(self, year_gan, ming_idx):
        year_gan_index = self.GAN.index(year_gan)
        return ((year_gan_index % 5) * 2 + 2 + ming_idx - 2) % 10

    def calc_wuxing_ju(self, year_gan, ming_idx):
        if year_gan not in self.GAN:
            raise ValueError("年干无效。")
        ming_gan_idx = self._get_ming_gan_index(year_gan, ming_idx)
        gan_part = ming_gan_idx // 2
        zhi_part = (ming_idx // 2) % 3
        ju_value = ((gan_part + zhi_part) % 5) + 1
        ju_num = [2, 6, 3, 4, 5][ju_value - 1]
        ju_names = {2: "水二局", 3: "木三局", 4: "金四局", 5: "土五局", 6: "火六局"}
        return {"number": ju_num, "name": ju_names[ju_num], "status": "简化版",
                "method": "沿用项目原有五虎遁与纳音五行局简化计算方法。"}

    def deploy_main_stars(self, lunar_day, ju_num):
        if lunar_day not in range(1, 31):
            raise ValueError("农历日期必须在 1 至 30 之间。")
        if ju_num not in [2, 3, 4, 5, 6]:
            raise ValueError("五行局必须为 2、3、4、5、6。")
        quotient = lunar_day // ju_num
        remainder = lunar_day % ju_num
        add_factor = ju_num - remainder if remainder != 0 else 0
        quotient = (lunar_day + add_factor) // ju_num
        if add_factor % 2 != 0:
            ziwei_idx = (1 + quotient - add_factor) % 12
        else:
            ziwei_idx = (1 + quotient + add_factor) % 12
        tianfu_idx = (14 - ziwei_idx) % 12

        stars_by_index = {i: [] for i in range(12)}
        for offset, star in self.ZIWEI_STARS.items():
            stars_by_index[(ziwei_idx - offset) % 12].append(star)
        for offset, star in self.TIANFU_STARS.items():
            stars_by_index[(tianfu_idx + offset) % 12].append(star)

        return {"ziwei_index": ziwei_idx, "ziwei_branch": self.ZHI[ziwei_idx],
                "tianfu_index": tianfu_idx, "tianfu_branch": self.ZHI[tianfu_idx],
                "stars_by_index": stars_by_index, "status": "简化版",
                "warnings": ["当前已安十四主星与常用辅煞星，但未包含全部杂曜。"]}

    def deploy_auxiliary_stars(self, year_gan, year_zhi, lunar_month, hour_zhi, main_stars_by_index):
        warnings = []
        aux = {i: [] for i in range(12)}

        def place(star, branch):
            if branch is None:
                warnings.append(f"{star}未能定位。")
                return
            aux[self.ZHI.index(branch)].append(star)

        place("文昌", self.WENCHANG_BY_GAN.get(year_gan))
        place("文曲", self.WENQU_BY_GAN.get(year_gan))
        lucun = self.LUCUN_BY_GAN.get(year_gan)
        place("禄存", lucun)
        if lucun:
            place("擎羊", self.ZHI[(self.ZHI.index(lucun) + 1) % 12])
            place("陀罗", self.ZHI[(self.ZHI.index(lucun) - 1) % 12])
        place("天魁", self.TIANKUI_BY_GAN.get(year_gan))
        place("天钺", self.TIANYUE_BY_GAN.get(year_gan))
        place("左辅", self.ZHI[(self.ZHI.index("辰") + (lunar_month - 1)) % 12])
        place("右弼", self.ZHI[(self.ZHI.index("戌") - (lunar_month - 1)) % 12])
        place("天马", self.TIANMA_BY_ZHI.get(year_zhi))

        hour_idx = self.ZHI.index(hour_zhi)
        huo_start = self.HUOXING_START.get(year_zhi)
        ling_start = self.LINGXING_START.get(year_zhi)
        if huo_start:
            place("火星", self.ZHI[(self.ZHI.index(huo_start) + hour_idx) % 12])
        if ling_start:
            place("铃星", self.ZHI[(self.ZHI.index(ling_start) + hour_idx) % 12])
        hai = self.ZHI.index("亥")
        place("地空", self.ZHI[(hai - hour_idx) % 12])
        place("地劫", self.ZHI[(hai + hour_idx) % 12])

        merged = {i: list(main_stars_by_index[i]) + aux[i] for i in range(12)}
        return merged, aux, warnings

    def _build_twelve_palaces(self, ming_idx, shen_idx, main_by_index, aux_by_index):
        palaces_by_branch = {}
        palaces_by_name = {}
        for offset, palace_name in enumerate(self.PALACE_NAMES):
            branch_index = (ming_idx - offset) % 12
            branch = self.ZHI[branch_index]
            main_stars = list(main_by_index[branch_index])
            aux_stars = list(aux_by_index.get(branch_index, []))
            all_stars = main_stars + aux_stars
            palace = {
                "name": palace_name,
                "branch": branch,
                "branch_index": branch_index,
                "is_ming_gong": branch_index == ming_idx,
                "is_shen_gong": branch_index == shen_idx,
                "main_stars": main_stars,
                "auxiliary_stars": aux_stars,
                "all_stars": all_stars,
                "is_empty": len(all_stars) == 0,
            }
            palaces_by_branch[branch] = palace
            palaces_by_name[palace_name] = palace
        return palaces_by_branch, palaces_by_name

    def _build_legacy_palaces(self, palaces_by_branch):
        formatted = {}
        for branch in self.ZHI:
            palace = palaces_by_branch[branch]
            tags = []
            if palace["is_ming_gong"]:
                tags.append("【命宫】")
            if palace["is_shen_gong"]:
                tags.append("【身宫】")
            star_text = " ".join(palace["all_stars"]) if palace["all_stars"] else "空宫"
            formatted[branch] = f"{''.join(tags)} {star_text}".strip()
        return formatted

    def _find_star_palace(self, palaces_by_branch, star_name):
        for branch, palace in palaces_by_branch.items():
            if star_name in palace["all_stars"]:
                return {"palace_name": palace["name"], "branch": branch, "status": "已定位"}
        return {"palace_name": None, "branch": None, "status": "未实现"}

    def _build_four_transformations(self, year_gan, palaces_by_branch):
        rule = self.FOUR_TRANSFORMATIONS.get(year_gan)
        if rule is None:
            return {"year_gan": year_gan, "items": {}, "warnings": ["年干无法匹配四化表。"]}
        items = {}
        warnings = []
        for name, star_name in rule.items():
            loc = self._find_star_palace(palaces_by_branch, star_name)
            if loc["status"] != "已定位":
                warnings.append(f"{name}化{star_name}：该星未在当前星曜安置范围内，宫位未生成。")
                status = "星曜未安"
            else:
                status = "已定位"
            items[name] = {"transform": name, "star": star_name,
                           "palace_name": loc["palace_name"], "branch": loc["branch"],
                           "status": status}
        return {"year_gan": year_gan, "items": items, "warnings": warnings}

    def _build_decadal_limits(self, palaces_by_branch, ming_idx, gender, year_gan, ju_number):
        year_yinyang = self.GAN_YINYANG.get(year_gan)
        if gender is None or year_yinyang is None:
            return {"direction": None, "start_age": None, "palaces": [],
                    "status": "未实现", "warning": "缺少有效性别或年干，无法判断大限顺逆。"}
        is_forward = (gender == "男" and year_yinyang == "阳") or (gender == "女" and year_yinyang == "阴")
        direction = "顺行" if is_forward else "逆行"
        start_age = ju_number
        seq = []
        for i in range(12):
            idx = (ming_idx + i) % 12 if is_forward else (ming_idx - i) % 12
            branch = self.ZHI[idx]
            palace = palaces_by_branch[branch]
            seq.append({
                "palace_name": palace["name"], "branch": branch,
                "start_age": start_age + i * 10, "end_age": start_age + i * 10 + 9,
                "status": "已计算",
            })
        return {"direction": direction, "year_gan_yinyang": year_yinyang,
                "start_age": start_age, "palaces": seq, "status": "简化版",
                "warning": "大限按五行局起限、每宫十年计算；未包含完整流派起限差异。"}

    def _build_annual_data(self, target_year, palaces_by_branch):
        if target_year is None:
            return {"target_year": None, "status": "未请求", "annual_palace": None,
                    "transformations": None, "warning": "未提供目标流年，未生成流年数据。"}
        try:
            target_year = int(target_year)
        except (TypeError, ValueError):
            return {"target_year": None, "status": "未实现", "annual_palace": None,
                    "transformations": None, "warning": "目标流年年份无效，未生成流年数据。"}
        liu_gan = self.GAN[(target_year - 4) % 10]
        liu_zhi = self.ZHI[(target_year - 4) % 12]
        liu_ming = palaces_by_branch.get(liu_zhi)
        annual_palace = {
            "liu_gan": liu_gan, "liu_zhi": liu_zhi,
            "palace_name": liu_ming["name"] if liu_ming else None,
            "branch": liu_zhi,
            "status": "已计算" if liu_ming else "未定位",
        }
        rule = self.FOUR_TRANSFORMATIONS.get(liu_gan, {})
        items = {}
        warnings = []
        for name, star in rule.items():
            loc = self._find_star_palace(palaces_by_branch, star)
            if loc["status"] != "已定位":
                warnings.append(f"流年{name}化{star}未定位。")
            items[name] = {"transform": name, "star": star,
                           "palace_name": loc["palace_name"], "branch": loc["branch"],
                           "status": loc["status"]}
        return {"target_year": target_year, "status": "简化版",
                "annual_palace": annual_palace,
                "transformations": {"liu_gan": liu_gan, "items": items, "warnings": warnings},
                "warning": "流年四化为基础版，按流年天干定位本命盘星曜，未实现流月、流日、流时。"}

    def _base_result(self, mode, status, warnings=None):
        return {"mode": mode, "status": status,
                "method": "紫微斗数简化版：使用 lunar_python 农历转换，"
                          "命身宫、十四主星、常用辅煞星、生年四化、大限、流年基础。",
                "school": "本项目简化紫微规则。不宣称完整覆盖三合、飞星、四化飞宫或全部杂曜流派。",
                "is_natal_chart": mode == "natal", "warnings": warnings or []}

    def run(self, dt, leap_month_rule="流派默认", user_lunar_month=None):
        warnings = ["本结果不是本命紫微盘，不用于判断本命命宫、身宫、夫妻宫和人生长期性格。",
                    "当前为问测时间辅助参考模式。"]
        try:
            dt = self._normalize_datetime(dt)
            leap_month_rule = self._normalize_leap_month_rule(leap_month_rule)
            if leap_month_rule is None:
                raise ValueError("闰月处理规则无效。")
            lunar_info = self.get_lunar_info(dt, leap_month_rule, user_lunar_month)
        except Exception as exc:
            result = self._base_result("auxiliary", "invalid",
                                       warnings + [f"辅助参考时间数据无法生成：{exc}"])
            result.update({"lunar_month": None, "lunar_day": None, "is_leap_corrected": None,
                           "wuxing_ju": None, "palaces": {}, "natal_data": None})
            return result

        warnings.extend(lunar_info["leap_month_handling"]["warnings"])
        result = self._base_result("auxiliary", "partial", warnings)
        result.update({
            "lunar_month": lunar_info["lunar_month"],
            "lunar_day": lunar_info["lunar_day"],
            "is_leap_corrected": lunar_info["is_leap_month"],
            "wuxing_ju": "辅助模式未计算",
            "palaces": {},
            "reference_datetime": lunar_info["solar_datetime"],
            "lunar_info": lunar_info,
            "leap_month_handling": lunar_info["leap_month_handling"],
            "ming_gong_branch": None,
            "shen_gong_branch": None,
            "spouse_palace": None,
            "twelve_palaces": {},
            "four_transformations": {},
            "decadal_limits": {"status": "不适用", "warning": "辅助模式不生成本命大限。"},
            "annual_data": {"status": "不适用", "warning": "辅助模式不生成本命流年。"},
            "natal_data": None,
        })
        return result

    def run_natal(self, birth_date, birth_time, birth_place, gender, timezone,
                  leap_month_rule, user_lunar_month=None, target_year=None):
        warnings = []
        missing_fields = []
        birth_dt = self._combine_birth_datetime(birth_date, birth_time)
        if birth_dt is None:
            missing_fields.append("出生日期和出生时间")
        normalized_place = self._normalize_birth_place(birth_place)
        if normalized_place is None:
            missing_fields.append("出生地点")
        normalized_gender = self._normalize_gender(gender)
        if normalized_gender is None:
            missing_fields.append("性别")
        normalized_timezone = self._normalize_timezone(timezone)
        if normalized_timezone is None:
            missing_fields.append("时区")
        normalized_leap_rule = self._normalize_leap_month_rule(leap_month_rule)
        if normalized_leap_rule is None:
            missing_fields.append("闰月处理规则")

        invalid_result = None
        if missing_fields:
            invalid_result = self._base_result(
                "natal", "invalid",
                ["本命紫微盘资料不完整，未生成本命盘。", "缺少或无效资料：" + "、".join(missing_fields)])
        if invalid_result is not None:
            invalid_result.update({
                "natal_data": None, "ming_gong_branch": None, "shen_gong_branch": None,
                "spouse_palace": None, "twelve_palaces": {}, "palaces": {},
                "four_transformations": {}, "decadal_limits": {"status": "未生成"},
                "annual_data": {"status": "未生成"}, "lunar_month": None, "lunar_day": None,
                "is_leap_corrected": None, "wuxing_ju": None})
            return invalid_result

        if normalized_place["longitude"] is None or normalized_place["latitude"] is None:
            warnings.append("出生地点未提供经纬度。当前不进行真太阳时校正，"
                            "仅按用户提供的当地民用出生时间排盘。")
        warnings.append("当前未实现真太阳时校正。出生时间接近时辰或子时边界时，"
                        "建议先完成地点经度与真太阳时校正。")

        try:
            lunar_info = self.get_lunar_info(birth_dt, normalized_leap_rule, user_lunar_month)
        except Exception as exc:
            result = self._base_result("natal", "invalid",
                                       warnings + [f"农历转换失败，未生成本命盘：{exc}"])
            result.update({"natal_data": None, "ming_gong_branch": None, "shen_gong_branch": None,
                           "spouse_palace": None, "twelve_palaces": {}, "palaces": {},
                           "four_transformations": {}, "decadal_limits": {"status": "未生成"},
                           "annual_data": {"status": "未生成"}, "lunar_month": None,
                           "lunar_day": None, "is_leap_corrected": None, "wuxing_ju": None})
            return result

        leap_info = lunar_info["leap_month_handling"]
        warnings.extend(leap_info["warnings"])
        lunar_month = lunar_info["lunar_month"]
        if lunar_month is None:
            result = self._base_result("natal", "invalid",
                                       warnings + ["闰月处理后未得到有效排盘月份，未生成本命盘。"])
            result.update({"natal_data": None, "ming_gong_branch": None, "shen_gong_branch": None,
                           "spouse_palace": None, "twelve_palaces": {}, "palaces": {},
                           "four_transformations": {}, "decadal_limits": {"status": "未生成"},
                           "annual_data": {"status": "未生成"}, "lunar_month": None,
                           "lunar_day": None, "is_leap_corrected": lunar_info["is_leap_month"],
                           "wuxing_ju": None})
            return result

        ming_idx, shen_idx = self.calc_palace_layout(lunar_month, lunar_info["hour_zhi_index"])
        wuxing_ju = self.calc_wuxing_ju(lunar_info["year_gan"], ming_idx)
        star_layout = self.deploy_main_stars(lunar_info["lunar_day"], wuxing_ju["number"])
        warnings.extend(star_layout["warnings"])

        all_stars, aux_stars, aux_warnings = self.deploy_auxiliary_stars(
            year_gan=lunar_info["year_gan"], year_zhi=lunar_info["year_zhi"],
            lunar_month=lunar_month, hour_zhi=lunar_info["hour_zhi"],
            main_stars_by_index=star_layout["stars_by_index"])
        warnings.extend(aux_warnings)

        palaces_by_branch, palaces_by_name = self._build_twelve_palaces(
            ming_idx, shen_idx, star_layout["stars_by_index"], aux_stars)
        legacy_palaces = self._build_legacy_palaces(palaces_by_branch)
        four_transformations = self._build_four_transformations(
            lunar_info["year_gan"], palaces_by_branch)
        warnings.extend(four_transformations["warnings"])

        decadal_limits = self._build_decadal_limits(
            palaces_by_branch, ming_idx, normalized_gender,
            lunar_info["year_gan"], wuxing_ju["number"])
        warnings.append(decadal_limits["warning"])

        annual_data = self._build_annual_data(target_year, palaces_by_branch)
        warnings.append(annual_data["warning"])

        spouse_palace = palaces_by_name["夫妻宫"]

        result = self._base_result("natal", "partial", warnings)
        result.update({
            "lunar_month": lunar_month,
            "lunar_day": lunar_info["lunar_day"],
            "is_leap_corrected": lunar_info["is_leap_month"],
            "wuxing_ju": wuxing_ju["name"],
            "palaces": legacy_palaces,
            "natal_data": {
                "birth_datetime": birth_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "birth_place": normalized_place,
                "gender": normalized_gender,
                "timezone": normalized_timezone,
                "time_basis": "用户提供的当地民用出生时间；未进行真太阳时校正。",
            },
            "lunar_info": lunar_info,
            "leap_month_handling": leap_info,
            "ming_gong_branch": self.ZHI[ming_idx],
            "ming_gong": palaces_by_name["命宫"],
            "shen_gong_branch": self.ZHI[shen_idx],
            "shen_gong": next(p for p in palaces_by_branch.values() if p["is_shen_gong"]),
            "twelve_palaces": palaces_by_branch,
            "twelve_palaces_by_name": palaces_by_name,
            "spouse_palace": spouse_palace,
            "main_star_layout": {
                "ziwei": {"branch": star_layout["ziwei_branch"], "index": star_layout["ziwei_index"]},
                "tianfu": {"branch": star_layout["tianfu_branch"], "index": star_layout["tianfu_index"]},
                "status": star_layout["status"],
            },
            "four_transformations": four_transformations,
            "四化": four_transformations,
            "decadal_limits": decadal_limits,
            "大限": decadal_limits,
            "annual_data": annual_data,
            "流年": annual_data,
            "rules": {
                "mode": "本命紫微盘简化版",
                "palace_layout": "寅宫起正月，顺数月，逆数时定命宫，顺数时定身宫。",
                "twelve_palaces": "从命宫起，按地支逆行安十二宫。",
                "main_stars": "紫微、天机、太阳、武曲、天同、廉贞、天府、太阴、贪狼、巨门、天相、天梁、七杀、破军。",
                "auxiliary_stars": "文昌、文曲、左辅、右弼、禄存、擎羊、陀罗、天魁、天钺、天马、火星、铃星、地空、地劫。",
                "four_transformations": "按生年天干四化表。",
                "leap_month": leap_info["rule_description"],
                "decadal_limits": "按五行局起限，每宫十年。",
                "annual_data": "流年命宫按流年地支定位，流年四化按流年天干定位本命盘星曜。",
            },
        })
        return result