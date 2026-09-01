# core_engine.py
# -*- coding: utf-8 -*-

import datetime
import math
from typing import Optional

import ephem


class PrecisionSolarEngine:
    """太阳黄经、节气区间和奇门月将计算。"""

    def __init__(self):
        self.terms = [
            "春分",
            "清明",
            "谷雨",
            "立夏",
            "小满",
            "芒种",
            "夏至",
            "小暑",
            "大暑",
            "立秋",
            "处暑",
            "白露",
            "秋分",
            "寒露",
            "霜降",
            "立冬",
            "小雪",
            "大雪",
            "冬至",
            "小寒",
            "大寒",
            "立春",
            "雨水",
            "惊蛰",
        ]

        self.yin_terms = {
            "夏至",
            "小暑",
            "大暑",
            "立秋",
            "处暑",
            "白露",
            "秋分",
            "寒露",
            "霜降",
            "立冬",
            "小雪",
            "大雪",
        }

        self.yang_map = {
            "冬至": [1, 7, 4],
            "小寒": [2, 8, 5],
            "大寒": [3, 9, 6],
            "立春": [8, 5, 2],
            "雨水": [9, 6, 3],
            "惊蛰": [1, 7, 4],
            "春分": [3, 9, 6],
            "清明": [4, 1, 7],
            "谷雨": [5, 2, 8],
            "立夏": [4, 1, 7],
            "小满": [5, 2, 8],
            "芒种": [6, 3, 9],
        }

        self.yin_map = {
            "夏至": [9, 3, 6],
            "小暑": [8, 2, 5],
            "大暑": [7, 1, 4],
            "立秋": [2, 5, 8],
            "处暑": [1, 4, 7],
            "白露": [9, 3, 6],
            "秋分": [7, 1, 4],
            "寒露": [6, 9, 3],
            "霜降": [5, 8, 2],
            "立冬": [6, 9, 3],
            "小雪": [5, 8, 2],
            "大雪": [4, 7, 1],
        }

        self.yue_jiang_list = [
            "戌",
            "酉",
            "申",
            "未",
            "午",
            "巳",
            "辰",
            "卯",
            "寅",
            "丑",
            "子",
            "亥",
        ]

    def get_solar_data(self, dt):
        """
        返回太阳黄经、节气区间、阴阳遁、局数映射和月将。

        这里接收的是 app.py 计算出的最终排盘时间。
        """
        if not isinstance(dt, datetime.datetime):
            raise TypeError(
                "get_solar_data() 需要 datetime.datetime 参数。"
            )

        # ephem 按 UTC 计算。项目沿用原有 UTC+8 接口。
        ephem_dt = dt - datetime.timedelta(hours=8)

        sun = ephem.Sun()
        sun.compute(ephem.Date(ephem_dt))

        solar_longitude = (
            math.degrees(
                float(ephem.Ecliptic(sun).lon)
            )
            % 360.0
        )

        term_index = int(solar_longitude // 15.0) % 24
        term_name = self.terms[term_index]

        dun_type = (
            "阴遁"
            if term_name in self.yin_terms
            else "阳遁"
        )

        ju_map = (
            self.yang_map
            if dun_type == "阳遁"
            else self.yin_map
        )

        yue_jiang_index = int(solar_longitude // 30.0) % 12
        yue_jiang = self.yue_jiang_list[
            yue_jiang_index
        ]

        return (
            solar_longitude,
            term_name,
            dun_type,
            ju_map,
            yue_jiang,
        )


class TimeAndGeo:
    """
    四柱计算模块。

    规则：
    - 年柱以立春为界；
    - 月柱使用太阳黄经节气区间；
    - 23:00 起子时换日；
    - 时干使用五鼠遁；
    - 旬首、旬空根据日柱计算。
    """

    GAN = list("甲乙丙丁戊己庚辛壬癸")
    ZHI = list("子丑寅卯辰巳午未申酉戌亥")

    BASE_DATE = datetime.date(1984, 2, 2)

    MONTH_ZHI = [
        "寅",
        "卯",
        "辰",
        "巳",
        "午",
        "未",
        "申",
        "酉",
        "戌",
        "亥",
        "子",
        "丑",
    ]

    XUN_KONG = {
        "甲子": "戌亥",
        "甲戌": "申酉",
        "甲申": "午未",
        "甲午": "辰巳",
        "甲辰": "寅卯",
        "甲寅": "子丑",
    }

    DAY_GAN_START_FOR_ZI = {
        "甲": 0,
        "己": 0,
        "乙": 2,
        "庚": 2,
        "丙": 4,
        "辛": 4,
        "丁": 6,
        "壬": 6,
        "戊": 8,
        "癸": 8,
    }

    def __init__(self):
        self.JIAZI = [
            self.GAN[i % 10] + self.ZHI[i % 12]
            for i in range(60)
        ]

    @staticmethod
    def normalize_longitude(
        solar_longitude: float,
    ) -> float:
        return float(solar_longitude) % 360.0

    def get_month_index(
        self,
        solar_longitude: Optional[float],
    ) -> int:
        """
        依据太阳黄经取得月序：

        0：寅月
        1：卯月
        ...
        11：丑月
        """
        if solar_longitude is None:
            raise ValueError(
                "四柱月柱必须提供真实太阳黄经，"
                "不能使用固定公历日期代替节气。"
            )

        longitude = self.normalize_longitude(
            solar_longitude
        )

        # 立春至惊蛰前为寅月。
        if longitude >= 315.0:
            return 0

        # 春分 0° 后依次进入卯月、辰月……
        return int(longitude // 30.0) + 1

    def get_year_pillar(
        self,
        dt: datetime.datetime,
        solar_longitude: Optional[float],
    ) -> str:
        """
        以立春为年界。

        300° 至 315° 为大寒至立春前，
        仍然属于上一干支年。
        """
        year = dt.year

        if solar_longitude is not None:
            longitude = self.normalize_longitude(
                solar_longitude
            )

            if 300.0 <= longitude < 315.0:
                year -= 1

        gan_index = (year - 4) % 10
        zhi_index = (year - 4) % 12

        return (
            self.GAN[gan_index]
            + self.ZHI[zhi_index]
        )

    def get_day_index(
        self,
        date_value: datetime.date,
    ) -> int:
        """1984-02-02 作为甲子日。"""
        return (
            date_value - self.BASE_DATE
        ).days % 60

    def get_xun_head(
        self,
        jiazi_index: int,
    ) -> str:
        """根据日柱取得旬首。"""
        xun_index = jiazi_index - (
            jiazi_index % 10
        )
        return self.JIAZI[xun_index]

    def get_pillars(
        self,
        dt: datetime.datetime,
        solar_longitude: Optional[float] = None,
    ):
        if not isinstance(dt, datetime.datetime):
            raise TypeError(
                "get_pillars() 需要 datetime.datetime 参数。"
            )

        # 23:00 至 23:59 作为早子时，日柱取次日。
        is_early_zi = dt.hour == 23

        day_date = dt.date()

        if is_early_zi:
            day_date += datetime.timedelta(days=1)

        effective_dt = datetime.datetime.combine(
            day_date,
            dt.time(),
        )

        year_pillar = self.get_year_pillar(
            effective_dt,
            solar_longitude,
        )

        year_gan_index = self.GAN.index(
            year_pillar[0]
        )

        month_index = self.get_month_index(
            solar_longitude
        )

        month_zhi = self.MONTH_ZHI[month_index]

        # 五虎遁：
        # 甲己丙作首，乙庚戊为头，丙辛从庚起，
        # 丁壬壬寅顺，若问戊癸何方发，甲寅之上好追求。
        first_month_gan_index = (
            year_gan_index * 2 + 2
        ) % 10

        month_gan_index = (
            first_month_gan_index + month_index
        ) % 10

        month_pillar = (
            self.GAN[month_gan_index]
            + month_zhi
        )

        day_index = self.get_day_index(day_date)

        day_gan = self.GAN[day_index % 10]
        day_zhi = self.ZHI[day_index % 12]
        day_pillar = day_gan + day_zhi

        # 子时为 23:00—00:59，丑时为 01:00—02:59。
        hour_zhi_index = ((dt.hour + 1) // 2) % 12
        hour_zhi = self.ZHI[hour_zhi_index]

        zi_gan_index = self.DAY_GAN_START_FOR_ZI[day_gan]
        hour_gan_index = (
            zi_gan_index + hour_zhi_index
        ) % 10

        hour_gan = self.GAN[hour_gan_index]
        hour_pillar = hour_gan + hour_zhi

        xun_head = self.get_xun_head(day_index)
        kong_wang = self.XUN_KONG[xun_head]

        if day_zhi in "子午卯酉":
            yuan_index = 0
        elif day_zhi in "寅申巳亥":
            yuan_index = 1
        else:
            yuan_index = 2

        return {
            "year": year_pillar,
            "month": month_pillar,
            "day": day_pillar,
            "hour": hour_pillar,

            "day_gan": day_gan,
            "day_zhi": day_zhi,
            "h_gan": hour_gan,
            "h_zhi": hour_zhi,

            "xun": xun_head,
            "kw": kong_wang,
            "yuan_idx": yuan_index,
            "is_early_zi": is_early_zi,

            "rules": {
                "year_boundary": "立春",
                "month_boundary": "真实太阳黄经节气",
                "zi_hour_day_change": "23:00",
                "kongwang_from": "日柱",
            },
        }


class QimenEngine:
    """
    奇门遁甲模块。

    当前采用：
    - 阳遁顺布、阴遁逆布；
    - 九宫编号沿用原项目：
      1坎、2坤、3震、4巽、5中、6乾、7兑、8艮、9离；
    - 三奇六仪顺序沿用原项目；
    - 八门、九星、八神使用原项目排列方式；
    - 旬空由旬首对应的六十甲子旬空表确定；
    - 值符、值使根据排局完成后的最终布局确定；
    - 日干、年干、年命、乙、六合、开门、生门均独立标记。

    旧接口兼容：

        run(ju, is_yang, xun, h_gan, h_zhi, kw)

    返回：

        layout, zhi_fu, zhi_shi

    新接口：

        run(
            ju,
            is_yang,
            xun,
            h_gan,
            h_zhi,
            kw,
            day_gan=None,
            year_gan=None,
            year_ming=None,
            user_mapping=None,
            return_details=False,
        )

    当 return_details=False 时，返回旧的三元组。
    当 return_details=True 时，返回：

        {
            "legacy_layout": ...,
            "layout": ...,
            "method": ...,
            ...
        }
    """

    PALACE_NAMES = {
        1: "坎",
        2: "坤",
        3: "震",
        4: "巽",
        5: "中",
        6: "乾",
        7: "兑",
        8: "艮",
        9: "离",
    }

    PALACE_NUMBERS = {
        value: key
        for key, value in PALACE_NAMES.items()
    }

    # 洛书九宫的八宫环。
    RING = [1, 8, 3, 4, 9, 2, 7, 6]

    STEMS = list("戊己庚辛壬癸丁丙乙")

    XUN_HEAD_TO_DUN_STEM = {
        "甲子": "戊",
        "甲戌": "己",
        "甲申": "庚",
        "甲午": "辛",
        "甲辰": "壬",
        "甲寅": "癸",
    }

    XUN_KONG = {
        "甲子": ["戌", "亥"],
        "甲戌": ["申", "酉"],
        "甲申": ["午", "未"],
        "甲午": ["辰", "巳"],
        "甲辰": ["寅", "卯"],
        "甲寅": ["子", "丑"],
    }

    STEM_TO_PALACE = {
        "戊": 1,
        "己": 2,
        "庚": 3,
        "辛": 4,
        "壬": 6,
        "癸": 7,
        "丁": 8,
        "丙": 9,
        "乙": 4,
    }

    STAR_BY_PALACE = {
        1: "天蓬",
        2: "天芮",
        3: "天冲",
        4: "天辅",
        5: "天禽",
        6: "天心",
        7: "天柱",
        8: "天任",
        9: "天英",
    }

    DOOR_SEQUENCE = [
        "休门",
        "生门",
        "伤门",
        "杜门",
        "景门",
        "死门",
        "惊门",
        "开门",
    ]

    DOOR_BY_PALACE = {
        1: "休门",
        2: "死门",
        3: "伤门",
        4: "杜门",
        5: "",
        6: "开门",
        7: "惊门",
        8: "生门",
        9: "景门",
    }

    YANG_GODS = [
        "值符",
        "螣蛇",
        "太阴",
        "六合",
        "白虎",
        "玄武",
        "九地",
        "九天",
    ]

    YIN_GODS = [
        "值符",
        "九天",
        "九地",
        "玄武",
        "白虎",
        "六合",
        "太阴",
        "螣蛇",
    ]

    PALACE_ZHI = {
        1: ["子"],
        2: ["未", "申"],
        3: ["卯"],
        4: ["辰", "巳"],
        5: [],
        6: ["戌", "亥"],
        7: ["酉"],
        8: ["寅", "丑"],
        9: ["午"],
    }

    def _normalize_xun_kong(self, xun, kw):
        warnings = []

        if isinstance(kw, str):
            supplied = [
                branch
                for branch in "子丑寅卯辰巳午未申酉戌亥"
                if branch in kw
            ]
        elif kw is None:
            supplied = []
        else:
            supplied = list(kw)

        calculated = self.XUN_KONG.get(xun, [])

        if calculated:
            if supplied and set(supplied) != set(calculated):
                warnings.append(
                    "传入旬空与旬首对应旬空不一致，"
                    "已采用旬首规则重新计算。"
                )
            return calculated, warnings

        if supplied:
            warnings.append(
                "旬首无法识别，暂采用调用方传入的旬空。"
            )
            return supplied, warnings

        warnings.append(
            "旬首和旬空均无法识别，空亡标记未完成。"
        )
        return [], warnings

    def _normalize_gan(self, gan):
        if gan is None:
            return None

        gan = str(gan).strip()

        if not gan:
            return None

        return gan[0]

    def _normalize_year_ming(self, year_ming):
        if year_ming is None:
            return None

        text = str(year_ming).strip()

        if not text:
            return None

        # 支持：
        # 1. 数字宫位；
        # 2. 坎、坤、震等宫名；
        # 3. 子、丑、寅等年命地支。
        try:
            number = int(text)
            if 1 <= number <= 9:
                return number
        except ValueError:
            pass

        if text in self.PALACE_NUMBERS:
            return self.PALACE_NUMBERS[text]

        for palace, branches in self.PALACE_ZHI.items():
            if text[0] in branches:
                return palace

        return None

    def _normalize_position(self, position):
        if position == 5:
            return 2
        return position

    def _advance_palace(self, palace, steps, forward):
        """
        按八宫环移动。
        中宫不参与八宫环。
        """
        palace = self._normalize_position(palace)

        try:
            index = self.RING.index(palace)
        except ValueError:
            return palace

        if forward:
            new_index = (index + steps) % 8
        else:
            new_index = (index - steps) % 8

        return self.RING[new_index]

    def _build_earth_stems(self, ju, is_yang):
        earth_stems = {
            palace: ""
            for palace in range(1, 10)
        }

        current = int(ju)

        sequence = (
            self.STEMS[:]
            if is_yang
            else [
                "戊",
                "乙",
                "丙",
                "丁",
                "癸",
                "壬",
                "辛",
                "庚",
                "己",
            ]
        )

        for stem in sequence:
            earth_stems[current] = stem

            if is_yang:
                current = current % 9 + 1
            else:
                current = (current - 2) % 9 + 1

        return earth_stems

    def _find_stem_palace(self, earth_stems, stem):
        if stem is None:
            return None

        for palace, value in earth_stems.items():
            if value == stem:
                return palace

        return None

    def _build_empty_layout(self, earth_stems, void_branches):
        layout = {}

        for palace in range(1, 10):
            layout[palace] = {
                "palace_number": palace,
                "palace": self.PALACE_NAMES[palace],
                "heaven_stem": "",
                "earth_stem": earth_stems.get(palace, ""),
                "star": "",
                "door": "",
                "deity": "",
                "god": "",
                "void_branches": list(void_branches),
                "void": any(
                    branch in void_branches
                    for branch in self.PALACE_ZHI[palace]
                ),
                "notes": [],
            }

        return layout

    def _place_stars(
        self,
        layout,
        earth_stems,
        hour_stem,
        xun_shou,
        is_yang,
    ):
        warnings = []

        dun_stem = self.XUN_HEAD_TO_DUN_STEM.get(
            xun_shou
        )

        if dun_stem is None:
            warnings.append(
                "旬首无法转换为值符天干，"
                "九星和值符定位可能不完整。"
            )
            dun_stem = "戊"

        leader_palace = self._find_stem_palace(
            earth_stems,
            dun_stem,
        )

        if leader_palace is None:
            warnings.append(
                f"旬首天干 {dun_stem} 未在地盘找到，"
                "值符定位未完成。"
            )
            leader_palace = 1

        hour_stem = self._normalize_gan(hour_stem)

        hour_palace = self._find_stem_palace(
            earth_stems,
            hour_stem,
        )

        if hour_stem is None:
            warnings.append(
                "未提供时干，无法严格确定值符转移位置。"
            )
            hour_palace = leader_palace

        if hour_palace is None:
            hour_palace = leader_palace

        shift = 0

        try:
            leader_index = self.RING.index(
                self._normalize_position(leader_palace)
            )
            hour_index = self.RING.index(
                self._normalize_position(hour_palace)
            )

            shift = hour_index - leader_index

        except ValueError:
            warnings.append(
                "值符转移宫位无法计算。"
            )

        for source_palace in self.RING:
            target_index = (
                self.RING.index(source_palace)
                + shift
            ) % 8

            target_palace = self.RING[target_index]

            layout[target_palace]["star"] = (
                self.STAR_BY_PALACE[source_palace]
            )

            layout[target_palace]["heaven_stem"] = (
                earth_stems[source_palace]
            )

        layout[5]["star"] = "天禽"
        layout[5]["heaven_stem"] = earth_stems.get(
            2,
            "",
        )

        return {
            "leader_palace": leader_palace,
            "hour_palace": hour_palace,
            "shift": shift,
            "warnings": warnings,
        }

    def _place_doors(
        self,
        layout,
        hour_zhi,
        xun_shou,
        is_yang,
    ):
        warnings = []

        zhi_list = list(
            "子丑寅卯辰巳午未申酉戌亥"
        )

        if not hour_zhi or hour_zhi not in zhi_list:
            warnings.append(
                "未提供有效时支，八门和值使无法严格定位。"
            )
            hour_index = 0
        else:
            hour_index = zhi_list.index(hour_zhi)

        xun_zhi = (
            xun_shou[1]
            if xun_shou and len(xun_shou) >= 2
            else None
        )

        if xun_zhi not in zhi_list:
            warnings.append(
                "旬首地支无法识别，值使定位存在不确定性。"
            )
            xun_index = 0
        else:
            xun_index = zhi_list.index(xun_zhi)

        # 保留现有项目的门定位方向规则。
        hour_difference = hour_index - xun_index

        if is_yang:
            door_reference = 1 + (
                hour_difference % 8
            )
        else:
            door_reference = 1 - (
                hour_difference % 8
            )

        door_reference = (
            (door_reference - 1) % 9
        ) + 1

        if door_reference == 5:
            door_reference = 2

        # 根据原始九宫门表确定值使门。
        zhi_shi_door = self.DOOR_BY_PALACE.get(
            door_reference,
            "",
        )

        if not zhi_shi_door:
            warnings.append(
                "值使门未能从门表中确定。"
            )
            zhi_shi_door = "休门"

        door_index = self.DOOR_SEQUENCE.index(
            zhi_shi_door
        )

        for offset in range(8):
            source_index = offset
            source_palace = self.RING[source_index]

            target_index = (
                self.RING.index(door_reference)
                + offset
            ) % 8

            target_palace = self.RING[target_index]

            if is_yang:
                actual_door_index = (
                    door_index + offset
                ) % 8
            else:
                actual_door_index = (
                    door_index - offset
                ) % 8

            layout[target_palace]["door"] = (
                self.DOOR_SEQUENCE[actual_door_index]
            )

        layout[5]["door"] = layout[2]["door"]

        return {
            "door_reference_palace": door_reference,
            "zhi_shi_door": zhi_shi_door,
            "warnings": warnings,
        }

    def _place_deities(
        self,
        layout,
        star_info,
        is_yang,
    ):
        warnings = []

        start_palace = star_info.get(
            "hour_palace"
        )

        if start_palace is None:
            warnings.append(
                "八神起点未确定。"
            )
            start_palace = 1

        start_palace = self._normalize_position(
            start_palace
        )

        try:
            start_index = self.RING.index(
                start_palace
            )
        except ValueError:
            warnings.append(
                "八神起点不在八宫环中。"
            )
            start_index = 0

        gods = (
            self.YANG_GODS
            if is_yang
            else self.YIN_GODS
        )

        for offset, god in enumerate(gods):
            if is_yang:
                index = (
                    start_index + offset
                ) % 8
            else:
                index = (
                    start_index - offset
                ) % 8

            palace = self.RING[index]
            layout[palace]["deity"] = god
            layout[palace]["god"] = god

        layout[5]["deity"] = layout[2]["deity"]
        layout[5]["god"] = layout[2]["god"]

        return warnings

    def _find_marker_palace(
        self,
        layout,
        *,
        stem=None,
        star=None,
        door=None,
        deity=None,
    ):
        for palace, data in layout.items():
            if stem is not None:
                if data["heaven_stem"] == stem:
                    return palace

            if star is not None:
                if data["star"] == star:
                    return palace

            if door is not None:
                if data["door"] == door:
                    return palace

            if deity is not None:
                if data["deity"] == deity:
                    return palace

        return None

    def _marker(self, value, palace):
        if palace is None:
            return {
                "value": value,
                "palace": None,
                "palace_name": None,
                "status": "未实现",
            }

        return {
            "value": value,
            "palace": palace,
            "palace_name": self.PALACE_NAMES[palace],
            "status": "已计算",
        }

    def _build_user_mapping(self, user_mapping):
        default_mapping = {
            "本人": {
                "rule": "日干",
                "requires_confirmation": False,
            },
            "年命": {
                "rule": "年干或年命",
                "requires_confirmation": True,
            },
            "感情对象": {
                "rule": "乙/六合",
                "requires_confirmation": True,
            },
            "工作关系": {
                "rule": "开门",
                "requires_confirmation": True,
            },
        }

        if not isinstance(user_mapping, dict):
            return default_mapping

        result = dict(default_mapping)

        for key, value in user_mapping.items():
            result[key] = value

        return result

    def run(
        self,
        ju,
        is_yang,
        xun,
        h_gan,
        h_zhi,
        kw,
        day_gan=None,
        year_gan=None,
        year_ming=None,
        user_mapping=None,
        return_details=False,
    ):
        warnings = []

        try:
            ju = int(ju)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"奇门局数无效：{ju}"
            ) from exc

        if ju not in range(1, 10):
            raise ValueError(
                f"奇门局数必须为 1 至 9，当前为：{ju}"
            )

        is_yang = bool(is_yang)
        yin_yang = "阳遁" if is_yang else "阴遁"

        day_gan = self._normalize_gan(day_gan)
        year_gan = self._normalize_gan(year_gan)

        void_branches, void_warnings = (
            self._normalize_xun_kong(xun, kw)
        )
        warnings.extend(void_warnings)

        if day_gan is None:
            warnings.append(
                "未传入日干，日干落宫标记为未实现。"
            )

        if year_gan is None:
            warnings.append(
                "未传入年干，年干落宫标记为未实现。"
            )

        if year_ming is None:
            warnings.append(
                "未传入年命，年命落宫标记为未实现。"
            )

        earth_stems = self._build_earth_stems(
            ju,
            is_yang,
        )

        layout = self._build_empty_layout(
            earth_stems,
            void_branches,
        )

        star_info = self._place_stars(
            layout,
            earth_stems,
            h_gan,
            xun,
            is_yang,
        )
        warnings.extend(star_info["warnings"])

        door_info = self._place_doors(
            layout,
            h_zhi,
            xun,
            is_yang,
        )
        warnings.extend(door_info["warnings"])

        deity_warnings = self._place_deities(
            layout,
            star_info,
            is_yang,
        )
        warnings.extend(deity_warnings)

        # 根据排布后的最终布局取值符和值使。
        zhi_fu_palace = self._find_marker_palace(
            layout,
            deity="值符",
        )

        zhi_shi_palace = self._find_marker_palace(
            layout,
            door=door_info["zhi_shi_door"],
        )

        if zhi_fu_palace is None:
            warnings.append(
                "排布完成后仍未找到值符落宫。"
            )

        if zhi_shi_palace is None:
            warnings.append(
                "排布完成后仍未找到值使落宫。"
            )

        day_gan_palace = self._find_marker_palace(
            layout,
            stem=day_gan,
        )

        year_gan_palace = self._find_marker_palace(
            layout,
            stem=year_gan,
        )

        year_ming_palace = self._normalize_year_ming(
            year_ming
        )

        if year_ming is not None and year_ming_palace is None:
            warnings.append(
                f"无法识别年命：{year_ming}。"
            )

        yi_palace = self._find_marker_palace(
            layout,
            stem="乙",
        )

        liu_he_palace = self._find_marker_palace(
            layout,
            deity="六合",
        )

        open_door_palace = self._find_marker_palace(
            layout,
            door="开门",
        )

        life_door_palace = self._find_marker_palace(
            layout,
            door="生门",
        )

        if day_gan_palace is None and day_gan:
            warnings.append(
                f"日干 {day_gan} 未在天盘干中找到。"
            )

        if year_gan_palace is None and year_gan:
            warnings.append(
                f"年干 {year_gan} 未在天盘干中找到。"
            )

        if not isinstance(user_mapping, dict):
            user_mapping = self._build_user_mapping(
                None
            )
        else:
            user_mapping = self._build_user_mapping(
                user_mapping
            )

        markers = {
            "day_gan": self._marker(
                day_gan,
                day_gan_palace,
            ),
            "year_gan": self._marker(
                year_gan,
                year_gan_palace,
            ),
            "year_ming": self._marker(
                year_ming,
                year_ming_palace,
            ),
            "yi": self._marker(
                "乙",
                yi_palace,
            ),
            "liu_he": self._marker(
                "六合",
                liu_he_palace,
            ),
            "open_door": self._marker(
                "开门",
                open_door_palace,
            ),
            "life_door": self._marker(
                "生门",
                life_door_palace,
            ),
            "zhi_fu": self._marker(
                "值符",
                zhi_fu_palace,
            ),
            "zhi_shi": self._marker(
                door_info["zhi_shi_door"],
                zhi_shi_palace,
            ),
        }

        # 中文别名，方便前端使用。
        markers["日干"] = markers["day_gan"]
        markers["年干"] = markers["year_gan"]
        markers["年命"] = markers["year_ming"]
        markers["乙"] = markers["yi"]
        markers["六合"] = markers["liu_he"]
        markers["开门"] = markers["open_door"]
        markers["生门"] = markers["life_door"]

        rich_palaces = {}

        for palace, data in layout.items():
            rich_palaces[
                data["palace"]
            ] = {
                "palace_number": palace,
                "heaven_stem": data["heaven_stem"],
                "earth_stem": data["earth_stem"],
                "star": data["star"],
                "door": data["door"],
                "deity": data["deity"],
                "god": data["god"],
                "void": data["void"],
                "void_branches": list(
                    data["void_branches"]
                ),
                "notes": list(data["notes"]),
            }

        method = (
            "转盘奇门简化排局"
            "；阳遁顺布、阴遁逆布"
            "；九星、八门、八神按本项目固定序列"
            "；值符和值使在最终布局完成后定位"
        )

        result = {
            "status": (
                "complete"
                if not warnings
                else "partial"
            ),
            "method": method,
            "school": "本项目转盘奇门规则",
            "yin_yang": yin_yang,
            "ju_number": ju,
            "xun_shou": xun,
            "void_branches": void_branches,
            "hour_gan": h_gan,
            "hour_branch": h_zhi,
            "day_gan": day_gan,
            "year_gan": year_gan,
            "year_ming": year_ming,
            "palaces": rich_palaces,
            "markers": markers,
            "user_mapping": user_mapping,
            "warnings": warnings,
            "rules": {
                "earth_stem": (
                    "地盘三奇六仪按局数和阴阳遁方向排布"
                ),
                "heaven_stem": (
                    "天盘干随九星从值符起点转移"
                ),
                "star": "九星按九宫固定星位转移",
                "door": (
                    "八门依据时支、旬首和阴阳遁方向排布"
                ),
                "deity": (
                    "八神从值符起点按阴阳遁方向排布"
                ),
                "zhi_fu": (
                    "排布完成后查找 deity == 值符 "
                    "的最终宫位"
                ),
                "zhi_shi": (
                    "排布完成后查找最终值使门的宫位"
                ),
                "void": (
                    "优先根据旬首使用六十甲子旬空表"
                ),
                "day_gan": (
                    "日干落宫仅依据最终天盘干查找"
                ),
                "year_gan": (
                    "年干落宫仅依据最终天盘干查找"
                ),
                "year_ming": (
                    "年命需要调用方提供年命地支或宫位"
                ),
                "user_mapping": (
                    "现实关系不硬编码为确定宫位，"
                    "由 user_mapping 独立配置"
                ),
            },
            "取用规则": {
                "本人": "日干",
                "年命": "年干或年命，必须由调用方确认",
                "感情对象": "乙/六合，仅作为候选取用",
                "工作关系": "开门，仅作为候选取用",
                "说明": (
                    "公司同事、普通朋友、外地朋友等现实关系"
                    "不会自动映射到固定宫位"
                ),
            },
        }

        # 保留旧 layout 数字键以及旧字段名。
        legacy_layout = {}

        for palace, data in layout.items():
            legacy_layout[palace] = {
                "di": data["earth_stem"],
                "earth_stem": data["earth_stem"],
                "tian": data["heaven_stem"],
                "heaven_stem": data["heaven_stem"],
                "star": data["star"],
                "door": data["door"],
                "god": data["deity"],
                "deity": data["deity"],
                "kw": data["void"],
                "void": data["void"],
                "palace": data["palace"],
                "palace_number": palace,
            }

        if not return_details:
            # 旧接口：
            # app.py 原有代码可以继续使用 q_layout、q_star、q_door。
            return (
                legacy_layout,
                (
                    layout[zhi_fu_palace]["star"]
                    if zhi_fu_palace is not None
                    else ""
                ),
                (
                    layout[zhi_shi_palace]["door"]
                    if zhi_shi_palace is not None
                    else ""
                ),
            )

        result["layout"] = legacy_layout
        result["legacy_layout"] = legacy_layout

        return result


class LiuYaoEngine:
    """
    六爻完整装卦模块。

    当前起卦方式：
        外部传入六个爻值，顺序必须为：
        初爻、二爻、三爻、四爻、五爻、上爻。

    爻值定义：
        6：老阴，阴爻，动爻，变为阳
        7：少阳，阳爻，不动
        8：少阴，阴爻，不动
        9：老阳，阳爻，动爻，变为阴

    规则：
        1. 初爻至三爻为下卦；
        2. 四爻至上爻为上卦；
        3. 使用传统八宫纳甲；
        4. 使用八宫卦变世应规则；
        5. 使用卦宫五行确定六亲；
        6. 使用日干确定六神；
        7. 使用月建、日辰做基础旺衰；
        8. 使用本宫卦的缺失六亲推伏神；
        9. 旬空必须由外部传入，不自行猜测。

    兼容旧接口：
        result["ben"]
        result["bian"]
        result["moves"]
        result["codes"]
    """

    GAN = list("甲乙丙丁戊己庚辛壬癸")
    ZHI = list("子丑寅卯辰巳午未申酉戌亥")

    TRIGRAM_BITS = {
        "乾": (1, 1, 1),
        "兑": (1, 1, 0),
        "离": (1, 0, 1),
        "震": (1, 0, 0),
        "巽": (0, 1, 1),
        "坎": (0, 1, 0),
        "艮": (0, 0, 1),
        "坤": (0, 0, 0),
    }

    BITS_TRIGRAM = {
        bits: name
        for name, bits in TRIGRAM_BITS.items()
    }

    TRIGRAM_WUXING = {
        "乾": "金",
        "兑": "金",
        "离": "火",
        "震": "木",
        "巽": "木",
        "坎": "水",
        "艮": "土",
        "坤": "土",
    }

    ZHI_WUXING = {
        "子": "水",
        "丑": "土",
        "寅": "木",
        "卯": "木",
        "辰": "土",
        "巳": "火",
        "午": "火",
        "未": "土",
        "申": "金",
        "酉": "金",
        "戌": "土",
        "亥": "水",
    }

    GAN_WUXING = {
        "甲": "木",
        "乙": "木",
        "丙": "火",
        "丁": "火",
        "戊": "土",
        "己": "土",
        "庚": "金",
        "辛": "金",
        "壬": "水",
        "癸": "水",
    }

    GENERATES = {
        "木": "火",
        "火": "土",
        "土": "金",
        "金": "水",
        "水": "木",
    }

    CONTROLS = {
        "木": "土",
        "土": "水",
        "水": "火",
        "火": "金",
        "金": "木",
    }

    SIX_GODS = [
        "青龙",
        "朱雀",
        "勾陈",
        "螣蛇",
        "白虎",
        "玄武",
    ]

    SIX_GOD_START = {
        "甲": 0,
        "乙": 0,
        "丙": 1,
        "丁": 1,
        "戊": 2,
        "己": 3,
        "庚": 4,
        "辛": 4,
        "壬": 5,
        "癸": 5,
    }

    # 八宫纳甲。
    # 每个卦的地支均按初爻至三爻排列。
    NAJIA = {
        "乾": {
            "inner_stem": "甲",
            "inner_branches": ["子", "寅", "辰"],
            "outer_stem": "壬",
            "outer_branches": ["午", "申", "戌"],
        },
        "坤": {
            "inner_stem": "乙",
            "inner_branches": ["未", "巳", "卯"],
            "outer_stem": "癸",
            "outer_branches": ["丑", "亥", "酉"],
        },
        "震": {
            "inner_stem": "庚",
            "inner_branches": ["子", "寅", "辰"],
            "outer_stem": "庚",
            "outer_branches": ["午", "申", "戌"],
        },
        "巽": {
            "inner_stem": "辛",
            "inner_branches": ["丑", "亥", "酉"],
            "outer_stem": "辛",
            "outer_branches": ["未", "巳", "卯"],
        },
        "坎": {
            "inner_stem": "戊",
            "inner_branches": ["寅", "辰", "午"],
            "outer_stem": "戊",
            "outer_branches": ["申", "戌", "子"],
        },
        "离": {
            "inner_stem": "己",
            "inner_branches": ["卯", "丑", "亥"],
            "outer_stem": "己",
            "outer_branches": ["酉", "未", "巳"],
        },
        "艮": {
            "inner_stem": "丙",
            "inner_branches": ["辰", "午", "申"],
            "outer_stem": "丙",
            "outer_branches": ["戌", "子", "寅"],
        },
        "兑": {
            "inner_stem": "丁",
            "inner_branches": ["巳", "卯", "丑"],
            "outer_stem": "丁",
            "outer_branches": ["亥", "酉", "未"],
        },
    }

    PALACE_TRIGRAMS = [
        "乾",
        "坎",
        "艮",
        "震",
        "巽",
        "离",
        "坤",
        "兑",
    ]

    XUN_KONG_BY_HEAD = {
        "甲子": ["戌", "亥"],
        "甲戌": ["申", "酉"],
        "甲申": ["午", "未"],
        "甲午": ["辰", "巳"],
        "甲辰": ["寅", "卯"],
        "甲寅": ["子", "丑"],
    }

    HEXAGRAM_NAMES = {
        "乾乾": "乾为天",
        "坤坤": "坤为地",
        "坎坎": "坎为水",
        "离离": "离为火",
        "艮艮": "艮为山",
        "震震": "震为雷",
        "巽巽": "巽为风",
        "兑兑": "兑为泽",

        "乾坤": "天地否",
        "坤乾": "地天泰",
        "坎离": "水火既济",
        "离坎": "火水未济",
        "艮坤": "山地剥",
        "坤艮": "地山谦",
        "震巽": "雷风恒",
        "巽震": "风雷益",
        "乾坎": "天水讼",
        "坎乾": "水天需",
        "乾艮": "天山遁",
        "艮乾": "山天大畜",
        "乾震": "天雷无妄",
        "震乾": "雷天大壮",
        "乾巽": "天风姤",
        "巽乾": "风天小畜",
        "乾离": "天火同人",
        "离乾": "火天大有",
        "乾兑": "天泽履",
        "兑乾": "泽天夬",

        "坤坎": "地水师",
        "坎坤": "水地比",
        "坤震": "地雷复",
        "震坤": "雷地豫",
        "坤巽": "地风升",
        "巽坤": "风地观",
        "坤离": "地火明夷",
        "离坤": "火地晋",
        "坤兑": "地泽临",
        "兑坤": "泽地萃",

        "坎艮": "水山蹇",
        "艮坎": "山水蒙",
        "坎震": "水雷屯",
        "震坎": "雷水解",
        "坎巽": "水风井",
        "巽坎": "风水涣",
        "坎兑": "水泽节",
        "兑坎": "泽水困",

        "离艮": "火山旅",
        "艮离": "山火贲",
        "离震": "火雷噬嗑",
        "震离": "雷火丰",
        "离巽": "火风鼎",
        "巽离": "风火家人",
        "离兑": "火泽睽",
        "兑离": "泽火革",

        "艮震": "山雷颐",
        "震艮": "雷山小过",
        "艮巽": "山风蛊",
        "巽艮": "风山渐",
        "艮兑": "山泽损",
        "兑艮": "泽山咸",
        "震兑": "雷泽归妹",
        "兑震": "泽雷随",
        "巽兑": "风泽中孚",
        "兑巽": "泽风大过",
    }

    def __init__(self):
        self.palace_gua_map = self._build_palace_gua_map()

    def _validate_codes(self, codes):
        if codes is None:
            raise ValueError("六爻 codes 不能为空。")

        if len(codes) != 6:
            raise ValueError(
                "六爻 codes 必须包含六个值，"
                "顺序为初爻至上爻。"
            )

        normalized = []

        for value in codes:
            try:
                value = int(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"无效爻值：{value}"
                ) from exc

            if value not in [6, 7, 8, 9]:
                raise ValueError(
                    f"爻值只能为 6、7、8、9，当前为 {value}"
                )

            normalized.append(value)

        return normalized

    def _get_gua_info(self, bits):
        lower_bits = tuple(bits[:3])
        upper_bits = tuple(bits[3:])

        lower_name = self.BITS_TRIGRAM.get(
            lower_bits,
            "",
        )

        upper_name = self.BITS_TRIGRAM.get(
            upper_bits,
            "",
        )

        key = upper_name + lower_name

        return {
            "key": key,
            "name": self.HEXAGRAM_NAMES.get(
                key,
                key,
            ),
            "upper": upper_name,
            "lower": lower_name,
            "upper_bits": list(upper_bits),
            "lower_bits": list(lower_bits),
            "bits": list(bits),
        }

    def _build_palace_gua_map(self):
        """
        建立六十四卦八宫映射。

        每宫顺序：
            本宫卦
            一世卦
            二世卦
            三世卦
            四世卦
            五世卦
            游魂卦
            归魂卦

        返回：
            {
                "卦键": {
                    "palace": "艮",
                    "shi_position": 4,
                    "sequence_name": "四世"
                }
            }
        """
        result = {}

        for palace in self.PALACE_TRIGRAMS:
            palace_bits = list(
                self.TRIGRAM_BITS[palace]
                + self.TRIGRAM_BITS[palace]
            )

            current = palace_bits[:]

            # 本宫卦。
            gua = self._get_gua_info(current)

            result[gua["key"]] = {
                "palace": palace,
                "shi_position": 6,
                "sequence_name": "本宫",
            }

            # 一世至五世。
            for line_index in range(5):
                current = current[:]
                current[line_index] = (
                    1 - current[line_index]
                )

                gua = self._get_gua_info(current)

                result[gua["key"]] = {
                    "palace": palace,
                    "shi_position": line_index + 1,
                    "sequence_name": (
                        f"{line_index + 1}世"
                    ),
                }

            # 游魂卦：
            # 五世卦基础上变第四爻。
            current = current[:]
            current[3] = 1 - current[3]

            gua = self._get_gua_info(current)

            result[gua["key"]] = {
                "palace": palace,
                "shi_position": 4,
                "sequence_name": "游魂",
            }

              # 归魂卦：
            # 游魂卦的下卦整体恢复为本宫下卦。
            current = current[:]
            current[0] = palace_bits[0]
            current[1] = palace_bits[1]
            current[2] = palace_bits[2]
            gua = self._get_gua_info(current)
            result[gua["key"]] = {
                "palace": palace,
                "shi_position": 3,
                "sequence_name": "归魂",
            }

        return result

    def _get_shi_ying(self, gua_key):
        palace_info = self.palace_gua_map.get(gua_key)

        if palace_info is None:
            return None, None, None

        shi_position = palace_info["shi_position"]

        # 应爻与世爻相隔三位。
        ying_position = (
            (shi_position + 2) % 6
        ) + 1

        return (
            shi_position,
            ying_position,
            palace_info,
        )

    def _get_najia(self, upper_name, lower_name):
        lower = self.NAJIA.get(lower_name)
        upper = self.NAJIA.get(upper_name)

        if lower is None or upper is None:
            raise ValueError(
                "上下卦无法匹配纳甲表。"
            )

        result = []

        # 初爻、二爻、三爻。
        for index in range(3):
            stem = lower["inner_stem"]
            branch = lower["inner_branches"][index]

            result.append(
                {
                    "stem": stem,
                    "branch": branch,
                    "pillar": stem + branch,
                    "part": "下卦",
                }
            )

        # 四爻、五爻、上爻。
        for index in range(3):
            stem = upper["outer_stem"]
            branch = upper["outer_branches"][index]

            result.append(
                {
                    "stem": stem,
                    "branch": branch,
                    "pillar": stem + branch,
                    "part": "上卦",
                }
            )

        return result

    def _relative(self, palace_element, branch):
        branch_element = self.ZHI_WUXING.get(branch)

        if not palace_element or not branch_element:
            return None

        if branch_element == palace_element:
            return "兄弟"

        if self.GENERATES[palace_element] == branch_element:
            return "子孙"

        if self.CONTROLS[palace_element] == branch_element:
            return "妻财"

        if self.GENERATES[branch_element] == palace_element:
            return "父母"

        if self.CONTROLS[branch_element] == palace_element:
            return "官鬼"

        return None

    def _six_god(self, day_gan, position):
        if not day_gan:
            return None

        day_gan = str(day_gan)[0]

        if day_gan not in self.SIX_GOD_START:
            return None

        start = self.SIX_GOD_START[day_gan]

        return self.SIX_GODS[
            (start + position - 1) % 6
        ]

    def _normalize_xun_kong(self, xun_kong):
        if xun_kong is None:
            return []

        if isinstance(xun_kong, str):
            return [
                branch
                for branch in self.ZHI
                if branch in xun_kong
            ]

        return list(xun_kong)

    def _get_strength(
        self,
        branch,
        month_branch=None,
        day_branch=None,
    ):
        """
        基础旺衰判断。

        这不是完整六爻旺衰评分系统，
        但会明确返回月建和日辰的基础作用。
        """
        if month_branch is None and day_branch is None:
            return {
                "label": "未计算",
                "month_relation": None,
                "day_relation": None,
                "complete": False,
            }

        branch_element = self.ZHI_WUXING.get(branch)
        month_element = self.ZHI_WUXING.get(month_branch)
        day_element = self.ZHI_WUXING.get(day_branch)

        month_relation = None
        day_relation = None

        if branch_element and month_element:
            if branch_element == month_element:
                month_relation = "同月建"
            elif self.GENERATES[month_element] == branch_element:
                month_relation = "月建生"
            elif self.CONTROLS[month_element] == branch_element:
                month_relation = "月建克"
            elif self.GENERATES[branch_element] == month_element:
                month_relation = "泄于月建"
            elif self.CONTROLS[branch_element] == month_element:
                month_relation = "克月建"

        if branch_element and day_element:
            if branch_element == day_element:
                day_relation = "同日辰"
            elif self.GENERATES[day_element] == branch_element:
                day_relation = "日辰生"
            elif self.CONTROLS[day_element] == branch_element:
                day_relation = "日辰克"
            elif self.GENERATES[branch_element] == day_element:
                day_relation = "泄于日辰"
            elif self.CONTROLS[branch_element] == day_element:
                day_relation = "克日辰"

        relations = [
            item
            for item in [
                month_relation,
                day_relation,
            ]
            if item
        ]

        if not relations:
            label = "基础关系未判"
        else:
            label = "、".join(relations)

        return {
            "label": label,
            "month_relation": month_relation,
            "day_relation": day_relation,
            "complete": (
                month_branch is not None
                and day_branch is not None
            ),
        }

    def _line_name(self, position):
        names = {
            1: "初爻",
            2: "二爻",
            3: "三爻",
            4: "四爻",
            5: "五爻",
            6: "上爻",
        }

        return names[position]

    def _build_visible_line(
        self,
        position,
        value,
        changed_bit,
        najia,
        palace_element,
        shi_position,
        ying_position,
        day_gan,
        month_branch,
        day_branch,
        xun_kong,
    ):
        yin_yang = (
            "阳"
            if value in [7, 9]
            else "阴"
        )

        changed_yin_yang = (
            "阳"
            if changed_bit == 1
            else "阴"
        )

        moving = value in [6, 9]
        branch = najia["branch"]

        if position == shi_position:
            role = "世"
        elif position == ying_position:
            role = "应"
        else:
            role = "普通"

        strength = self._get_strength(
            branch=branch,
            month_branch=month_branch,
            day_branch=day_branch,
        )

        notes = []

        if moving:
            notes.append("动爻")

        if branch in xun_kong:
            notes.append("旬空")

        if role == "世":
            notes.append("世爻")

        if role == "应":
            notes.append("应爻")

        return {
            "position": position,
            "name": self._line_name(position),
            "value": value,
            "yin_yang": yin_yang,
            "moving": moving,
            "changed_yin_yang": changed_yin_yang,
            "changed": {
                "yin_yang": changed_yin_yang,
                "value": changed_bit,
            },
            "stem": najia["stem"],
            "branch": branch,
            "najia": najia["pillar"],
            "part": najia["part"],
            "relative": self._relative(
                palace_element,
                branch,
            ),
            "six_god": self._six_god(
                day_gan,
                position,
            ),
            "role": role,
            "void": branch in xun_kong,
            "hidden": False,
            "strength": strength,
            "notes": notes,
        }

    def _build_hidden_lines(
        self,
        palace_name,
        visible_lines,
        xun_kong,
        month_branch,
        day_branch,
    ):
        """
        计算伏神。

        规则：
        - 伏神取本卦所属八宫的本宫卦；
        - 先为本宫卦装纳甲；
        - 计算本宫卦六亲；
        - 找出本卦明爻中缺少的六亲；
        - 将缺少的六亲按爻位顺序放置于对应明爻之下。

        返回：
            hidden_lines：伏神列表
            hidden_by_position：按明爻位置组织的伏神映射
        """
        hidden_lines = []
        hidden_by_position = {
            position: []
            for position in range(1, 7)
        }

        if palace_name is None:
            return hidden_lines, hidden_by_position

        palace_bits = list(
            self.TRIGRAM_BITS[palace_name]
            + self.TRIGRAM_BITS[palace_name]
        )

        palace_gua = self._get_gua_info(palace_bits)

        palace_najia = self._get_najia(
            palace_gua["upper"],
            palace_gua["lower"],
        )

        palace_element = self.TRIGRAM_WUXING[
            palace_name
        ]

        visible_relatives = [
            line.get("relative")
            for line in visible_lines
            if line.get("relative")
        ]

        all_relatives = [
            "父母",
            "兄弟",
            "子孙",
            "妻财",
            "官鬼",
        ]

        missing_relatives = [
            relative
            for relative in all_relatives
            if relative not in visible_relatives
        ]

        # 将伏神按缺失六亲与本宫卦爻位顺序配对。
        hidden_index = 0

        for position, najia in enumerate(
            palace_najia,
            start=1,
        ):
            relative = self._relative(
                palace_element,
                najia["branch"],
            )

            if relative not in missing_relatives:
                continue

            if hidden_index >= len(missing_relatives):
                break

            relative = missing_relatives[hidden_index]
            hidden_index += 1

            strength = self._get_strength(
                branch=najia["branch"],
                month_branch=month_branch,
                day_branch=day_branch,
            )

            hidden_line = {
                "position": position,
                "name": self._line_name(position),
                "value": None,
                "yin_yang": None,
                "moving": False,
                "changed_yin_yang": None,
                "changed": None,
                "stem": najia["stem"],
                "branch": najia["branch"],
                "najia": najia["pillar"],
                "part": najia["part"],
                "relative": relative,
                "six_god": None,
                "role": "伏神",
                "void": najia["branch"] in xun_kong,
                "hidden": True,
                "strength": strength,
                "notes": [
                    "伏神",
                    "取本宫卦",
                    "安于对应明爻之下",
                ],
            }

            hidden_lines.append(hidden_line)
            hidden_by_position[position].append(
                hidden_line
            )

        return hidden_lines, hidden_by_position

    def process(
        self,
        codes,
        month_branch=None,
        day_branch=None,
        day_gan=None,
        xun_kong=None,
        **kwargs,
    ):
        """
        完整处理六爻。

        兼容旧调用：

            process(codes)

        推荐新调用：

            process(
                codes,
                month_branch="寅",
                day_branch="午",
                day_gan="甲",
                xun_kong=["辰", "巳"],
            )

        兼容参数别名：

            month_zhi
            day_zhi
            kong_wang
        """
        warnings = []

        if month_branch is None:
            month_branch = kwargs.get("month_zhi")

        if day_branch is None:
            day_branch = kwargs.get("day_zhi")

        if xun_kong is None:
            xun_kong = kwargs.get("kong_wang")

        normalized_codes = self._validate_codes(codes)

        if month_branch is None:
            warnings.append(
                "未提供月建，无法计算月建旺衰。"
            )

        if day_branch is None:
            warnings.append(
                "未提供日辰，无法计算日辰作用。"
            )

        if day_gan is None:
            warnings.append(
                "未提供日干，无法计算六神。"
            )

        if xun_kong is None:
            warnings.append(
                "未提供旬空，无法判断旬空。"
            )

        xun_kong_list = self._normalize_xun_kong(
            xun_kong
        )

        original_bits = []
        changed_bits = []
        moving_lines = []

        for value in normalized_codes:
            original_bit = (
                1
                if value in [7, 9]
                else 0
            )

            changed_bit = original_bit

            if value == 6:
                changed_bit = 1
            elif value == 9:
                changed_bit = 0

            original_bits.append(original_bit)
            changed_bits.append(changed_bit)

        original_gua = self._get_gua_info(
            original_bits
        )

        changed_gua = self._get_gua_info(
            changed_bits
        )

        for index, value in enumerate(
            normalized_codes
        ):
            if value in [6, 9]:
                moving_lines.append(index + 1)

        shi_position, ying_position, palace_info = (
            self._get_shi_ying(
                original_gua["key"]
            )
        )

        if palace_info is None:
            palace_name = None
            palace_element = None

            warnings.append(
                "本卦未匹配到八宫世应表，"
                "未生成世爻、应爻和伏神。"
            )
        else:
            palace_name = palace_info["palace"]
            palace_element = self.TRIGRAM_WUXING[
                palace_name
            ]

        najia_info = self._get_najia(
            original_gua["upper"],
            original_gua["lower"],
        )

        lines = []

        for index, value in enumerate(
            normalized_codes
        ):
            line = self._build_visible_line(
                position=index + 1,
                value=value,
                changed_bit=changed_bits[index],
                najia=najia_info[index],
                palace_element=palace_element,
                shi_position=shi_position,
                ying_position=ying_position,
                day_gan=day_gan,
                month_branch=month_branch,
                day_branch=day_branch,
                xun_kong=xun_kong_list,
            )

            lines.append(line)

        hidden_lines, hidden_by_position = (
            self._build_hidden_lines(
                palace_name=palace_name,
                visible_lines=lines,
                xun_kong=xun_kong_list,
                month_branch=month_branch,
                day_branch=day_branch,
            )
        )

        # 把伏神附加到对应明爻的数据中，
        # 方便前端逐爻显示和 JSON 序列化。
        for line in lines:
            position = line["position"]

            line["hidden_lines"] = (
                hidden_by_position.get(
                    position,
                    [],
                )
            )

        if palace_info is not None:
            sequence_name = palace_info[
                "sequence_name"
            ]
        else:
            sequence_name = None

        if warnings:
            status = "partial"
        else:
            status = "complete"

        return {
            # 旧字段：保持兼容。
            "ben": original_gua["name"],
            "bian": changed_gua["name"],
            "moves": moving_lines,
            "codes": normalized_codes,

            # 状态。
            "status": status,
            "warnings": warnings,

            # 起卦和卦象信息。
            "method": (
                "六爻摇卦；"
                "输入顺序为初爻至上爻；"
                "6老阴、7少阳、8少阴、9老阳"
            ),

            "gua": {
                "ben": original_gua["name"],
                "bian": changed_gua["name"],
                "ben_key": original_gua["key"],
                "bian_key": changed_gua["key"],
                "upper": original_gua["upper"],
                "lower": original_gua["lower"],
                "upper_bits": original_gua["upper_bits"],
                "lower_bits": original_gua["lower_bits"],
                "ben_bits": original_gua["bits"],
                "bian_bits": changed_gua["bits"],
            },

            "本卦": original_gua["name"],
            "变卦": changed_gua["name"],
            "动爻": moving_lines,
            "变爻": [
                line
                for line in lines
                if line["moving"]
            ],

            # 六爻逐爻结构。
            "lines": lines,

            # 伏神单独返回，便于序列化。
            "hidden_lines": hidden_lines,
            "伏神": hidden_lines,

            # 世应。
            "shi_position": shi_position,
            "ying_position": ying_position,
            "世爻": shi_position,
            "应爻": ying_position,

            # 八宫。
            "palace": palace_name,
            "palace_element": palace_element,
            "gua_sequence": sequence_name,

            # 时间辅助信息。
            "month_branch": month_branch,
            "day_branch": day_branch,
            "day_gan": day_gan,
            "xun_kong": xun_kong_list,

            "月建": month_branch,
            "日辰": day_branch,
            "旬空": xun_kong_list,

            # 规则说明。
            "rules": {
                "method": (
                    "外部传入六个爻值，"
                    "顺序为初爻至上爻"
                ),
                "line_values": {
                    "6": "老阴，阴变阳",
                    "7": "少阳，不变",
                    "8": "少阴，不变",
                    "9": "老阳，阳变阴",
                },
                "line_order": (
                    "codes[0]为初爻，"
                    "codes[5]为上爻"
                ),
                "trigram_order": (
                    "初爻至三爻为下卦，"
                    "四爻至上爻为上卦"
                ),
                "najia": "传统八宫纳甲",
                "relative": (
                    "以本卦所属卦宫五行为我，"
                    "根据纳甲地支五行确定六亲"
                ),
                "shi_ying": (
                    "采用八宫卦变世应规则；"
                    "世爻位置从初爻1至上爻6"
                ),
                "six_gods": (
                    "根据日干起六神，"
                    "按青龙、朱雀、勾陈、螣蛇、"
                    "白虎、玄武顺序排列"
                ),
                "month_strength": (
                    "根据月建、日辰与爻支五行"
                    "进行基础旺衰关系判断"
                ),
                "xun_kong": (
                    "旬空由外部传入，"
                    "不根据不完整信息自行猜测"
                ),
                "hidden_gods": (
                    "从本宫卦取伏神，"
                    "根据本卦缺失六亲安于对应明爻之下"
                ),
            },

            # 兼容之前中文键名的规则字段。
            "装卦规则": {
                "起卦方式": (
                    "六枚爻值，"
                    "顺序为初爻至上爻"
                ),
                "爻值": {
                    "6": "老阴，动，变阳",
                    "7": "少阳，不动",
                    "8": "少阴，不动",
                    "9": "老阳，动，变阴",
                },
                "上下卦": (
                    "初爻至三爻为下卦，"
                    "四爻至上爻为上卦"
                ),
                "纳甲": "传统八宫纳甲",
                "六亲": (
                    "以卦宫五行为我，"
                    "按纳甲地支五行确定"
                ),
                "六神": (
                    "按日干起六神"
                ),
                "世应": (
                    "八宫卦变世应规则"
                ),
                "伏神": (
                    "从本宫卦取缺失六亲，"
                    "安于对应明爻之下"
                ),
                "旺衰": (
                    "基于月建和日辰的基础关系，"
                    "不是完整量化评分"
                ),
                "旬空": (
                    "由外部传入旬空"
                ),
            },
        }
