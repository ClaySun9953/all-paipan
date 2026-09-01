# -*- coding: utf-8 -*-

"""
大六壬模块（完整替换版）。

本版本实现九宗门决策流程：
贼克（元首/重审）、比用、涉害、遥克（蒿矢/弹射）、
昴星、别责、八专、伏吟、反吟。

兼容旧调用：
    engine.run(yue_jiang, hour_zhi, day_gan, day_zhi, xun_shou=..., xun_kong=...)

保留旧字段：
    tian_pan / jiang_pan / ji_gong / sike / san_chuan / san_chuan_rule

新增字段：
    method / four_lessons / three_transmissions /
    heaven_plate_by_earth / earth_palace_of_heaven /
    generals / six_relations / course_type / warnings

方向约定：
    heaven_plate_by_earth: 地盘支 -> 天盘支
    earth_palace_of_heaven: 天盘支 -> 地盘支
"""


class DaLiuRenEngine:
    """大六壬排盘引擎。"""

    ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]

    JI_GONG = {
        "甲": "寅", "乙": "辰", "丙": "巳", "戊": "巳", "丁": "未",
        "己": "未", "庚": "申", "辛": "戌", "壬": "亥", "癸": "丑",
    }

    ZHI_WUXING = {
        "寅": "木", "卯": "木", "巳": "火", "午": "火", "申": "金", "酉": "金",
        "亥": "水", "子": "水", "辰": "土", "戌": "土", "丑": "土", "未": "土",
    }
    GAN_WUXING = {
        "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
        "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水",
    }
    GENERATES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
    CONTROLS = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

    XUN_KONG = {
        "甲子": ["戌", "亥"], "甲戌": ["申", "酉"], "甲申": ["午", "未"],
        "甲午": ["辰", "巳"], "甲辰": ["寅", "卯"], "甲寅": ["子", "丑"],
    }

    TIAN_JIANG = ["贵人", "螣蛇", "朱雀", "六合", "勾陈", "青龙",
                  "天空", "白虎", "太常", "玄武", "太阴", "天后"]

    GUI_REN_START = {
        "甲": {"day": "丑", "night": "未"}, "乙": {"day": "子", "night": "申"},
        "丙": {"day": "亥", "night": "酉"}, "丁": {"day": "亥", "night": "酉"},
        "戊": {"day": "丑", "night": "未"}, "己": {"day": "子", "night": "申"},
        "庚": {"day": "丑", "night": "未"}, "辛": {"day": "午", "night": "寅"},
        "壬": {"day": "巳", "night": "卯"}, "癸": {"day": "巳", "night": "卯"},
    }

    # 九宗门辅助表。
    ZHI_XING = {
        "子": "卯", "卯": "子",
        "寅": "巳", "巳": "申", "申": "寅",
        "丑": "戌", "戌": "未", "未": "丑",
        "辰": "辰", "午": "午", "酉": "酉", "亥": "亥",
    }
    ZHI_CHONG = {
        "子": "午", "午": "子", "丑": "未", "未": "丑",
        "寅": "申", "申": "寅", "卯": "酉", "酉": "卯",
        "辰": "戌", "戌": "辰", "巳": "亥", "亥": "巳",
    }
    WU_HE = {"甲": "己", "己": "甲", "乙": "庚", "庚": "乙", "丙": "辛",
             "辛": "丙", "丁": "壬", "壬": "丁", "戊": "癸", "癸": "戊"}
    SAN_HE = {
        "寅": ["寅", "午", "戌"], "午": ["寅", "午", "戌"], "戌": ["寅", "午", "戌"],
        "申": ["申", "子", "辰"], "子": ["申", "子", "辰"], "辰": ["申", "子", "辰"],
        "巳": ["巳", "酉", "丑"], "酉": ["巳", "酉", "丑"], "丑": ["巳", "酉", "丑"],
        "亥": ["亥", "卯", "未"], "卯": ["亥", "卯", "未"], "未": ["亥", "卯", "未"],
    }
    TIANMA_BY_ZHI = {
        "寅": "申", "午": "申", "戌": "申",
        "申": "寅", "子": "寅", "辰": "寅",
        "巳": "亥", "酉": "亥", "丑": "亥",
        "亥": "巳", "卯": "巳", "未": "巳",
    }
    MENG = {"寅", "申", "巳", "亥"}
    ZHONG = {"子", "午", "卯", "酉"}
    BA_ZHUAN_DAYS = {"甲寅", "丁未", "己未", "庚申", "癸丑"}

    def __init__(self):
        self._validate_static_tables()

    def _validate_static_tables(self):
        if len(self.ZHI) != 12 or len(self.GAN) != 10 or len(self.TIAN_JIANG) != 12:
            raise ValueError("六壬基础表配置错误。")
        if set(self.ZHI_WUXING.keys()) != set(self.ZHI):
            raise ValueError("地支五行表必须覆盖全部地支。")

    def _normalize_gan(self, gan):
        if gan is None:
            return None
        text = str(gan).strip()
        if not text:
            return None
        gan = text[0]
        return gan if gan in self.GAN else None

    def _normalize_zhi(self, zhi):
        if zhi is None:
            return None
        text = str(zhi).strip()
        if not text:
            return None
        zhi = text[-1]
        return zhi if zhi in self.ZHI else None

    def _normalize_xun(self, xun):
        if xun is None:
            return None
        text = str(xun).strip()
        return text if text in self.XUN_KONG else None

    def _zhi_yinyang(self, zhi):
        return "阳" if zhi in ("子", "寅", "辰", "午", "申", "戌") else "阴"

    def _gan_yinyang(self, gan):
        return "阳" if gan in ("甲", "丙", "戊", "庚", "壬") else "阴"

    def _get_xun_kong_from_xun(self, xun):
        normalized_xun = self._normalize_xun(xun)
        return list(self.XUN_KONG[normalized_xun]) if normalized_xun else []

    def _check_ke(self, upper_zhi, lower_zhi):
        upper_element = self.ZHI_WUXING.get(upper_zhi)
        lower_element = self.ZHI_WUXING.get(lower_zhi)
        if upper_element is None or lower_element is None:
            return "未知"
        if self.CONTROLS[upper_element] == lower_element:
            return "上克下"
        if self.CONTROLS[lower_element] == upper_element:
            return "下贼上"
        if self.GENERATES[upper_element] == lower_element:
            return "上生下"
        if self.GENERATES[lower_element] == upper_element:
            return "下生上"
        if upper_element == lower_element:
            return "比和"
        return "未知"

    def _six_relation(self, day_gan, branch):
        day_gan = self._normalize_gan(day_gan)
        branch = self._normalize_zhi(branch)
        if day_gan is None or branch is None:
            return {"relation": None, "status": "未实现", "reason": "缺少有效日干或地支"}
        day_element = self.GAN_WUXING[day_gan]
        branch_element = self.ZHI_WUXING[branch]
        if branch_element == day_element:
            relation = "兄弟"
        elif self.GENERATES[day_element] == branch_element:
            relation = "子孙"
        elif self.CONTROLS[day_element] == branch_element:
            relation = "妻财"
        elif self.GENERATES[branch_element] == day_element:
            relation = "父母"
        elif self.CONTROLS[branch_element] == day_element:
            relation = "官鬼"
        else:
            relation = None
        return {"relation": relation, "day_gan": day_gan, "day_element": day_element,
                "branch": branch, "branch_element": branch_element,
                "status": "已计算" if relation is not None else "未实现"}

    def _is_daytime(self, hour_zhi):
        return hour_zhi in ["卯", "辰", "巳", "午", "未", "申"]

    def _get_tian_jiang(self, day_gan, hour_zhi, tian_pan):
        warnings = []
        day_gan = self._normalize_gan(day_gan)
        hour_zhi = self._normalize_zhi(hour_zhi)
        if day_gan is None or hour_zhi is None:
            return {"generals_by_heaven": {}, "generals_by_earth": {},
                    "gui_ren_start": None, "warnings": ["日干或时支无效，无法排天将。"]}
        is_daytime = self._is_daytime(hour_zhi)
        gui_ren_start = self.GUI_REN_START[day_gan]["day" if is_daytime else "night"]
        earth_palace_of_heaven = {h: e for e, h in tian_pan.items()}
        gui_ren_earth = earth_palace_of_heaven.get(gui_ren_start)
        if gui_ren_earth is None:
            warnings.append("贵人起点未出现在天盘反向映射中。")
            return {"generals_by_heaven": {}, "generals_by_earth": {},
                    "gui_ren_start": gui_ren_start, "warnings": warnings}
        forward = gui_ren_earth in ["亥", "子", "丑", "寅", "卯", "辰"]
        earth_index = self.ZHI.index(gui_ren_earth)
        generals_by_heaven = {}
        for index in range(12):
            heaven_index = (earth_index + index) % 12 if forward else (earth_index - index) % 12
            generals_by_heaven[self.ZHI[heaven_index]] = self.TIAN_JIANG[index]
        generals_by_earth = {e: generals_by_heaven.get(h) for e, h in tian_pan.items()}
        return {"generals_by_heaven": generals_by_heaven, "generals_by_earth": generals_by_earth,
                "gui_ren_start": gui_ren_start, "gui_ren_earth": gui_ren_earth,
                "forward": forward, "warnings": warnings}

    def _build_tian_pan(self, yue_jiang, hour_zhi):
        yue_jiang = self._normalize_zhi(yue_jiang)
        hour_zhi = self._normalize_zhi(hour_zhi)
        if yue_jiang is None or hour_zhi is None:
            raise ValueError("月将和时支必须是有效地支。")
        shift = (self.ZHI.index(yue_jiang) - self.ZHI.index(hour_zhi)) % 12
        heaven_plate_by_earth = {}
        for earth_index, earth_branch in enumerate(self.ZHI):
            heaven_plate_by_earth[earth_branch] = self.ZHI[(earth_index + shift) % 12]
        earth_palace_of_heaven = {h: e for e, h in heaven_plate_by_earth.items()}
        return heaven_plate_by_earth, earth_palace_of_heaven, shift

    def _get_upper_god(self, branch, heaven_plate_by_earth):
        branch = self._normalize_zhi(branch)
        return heaven_plate_by_earth.get(branch) if branch else None

    def _build_four_lessons(self, day_gan, day_zhi, heaven_plate_by_earth):
        warnings = []
        day_gan = self._normalize_gan(day_gan)
        day_zhi = self._normalize_zhi(day_zhi)
        if day_gan is None or day_zhi is None:
            return [], ["日干或日支无效，无法建立四课。"]
        gan_palace = self.JI_GONG.get(day_gan)
        if gan_palace is None:
            return [], [f"日干 {day_gan} 没有有效寄宫。"]
        lesson1_bottom = gan_palace
        lesson1_top = self._get_upper_god(lesson1_bottom, heaven_plate_by_earth)
        lesson2_bottom = lesson1_top
        lesson2_top = self._get_upper_god(lesson2_bottom, heaven_plate_by_earth)
        lesson3_bottom = day_zhi
        lesson3_top = self._get_upper_god(lesson3_bottom, heaven_plate_by_earth)
        lesson4_bottom = lesson3_top
        lesson4_top = self._get_upper_god(lesson4_bottom, heaven_plate_by_earth)
        lessons = [
            {"index": 1, "name": "一课", "kind": "日干阳", "bottom": lesson1_bottom, "top": lesson1_top},
            {"index": 2, "name": "二课", "kind": "日干阴", "bottom": lesson2_bottom, "top": lesson2_top},
            {"index": 3, "name": "三课", "kind": "日支阳", "bottom": lesson3_bottom, "top": lesson3_top},
            {"index": 4, "name": "四课", "kind": "日支阴", "bottom": lesson4_bottom, "top": lesson4_top},
        ]
        for lesson in lessons:
            lesson["relation"] = self._check_ke(lesson["top"], lesson["bottom"])
            lesson["bottom_element"] = self.ZHI_WUXING.get(lesson["bottom"])
            lesson["top_element"] = self.ZHI_WUXING.get(lesson["top"])
        if any(l["top"] is None for l in lessons):
            warnings.append("四课中存在无法映射的上神。")
        return lessons, warnings

    # ---------- 九宗门初传决策 ----------

    def _bi_yong(self, candidates, day_gan):
        target = self._gan_yinyang(day_gan)
        same = [l for l in candidates if self._zhi_yinyang(l["top"]) == target]
        return same or candidates

    def _she_hai_depth(self, top_zhi):
        element = self.ZHI_WUXING.get(top_zhi)
        if element is None:
            return 0
        start = self.ZHI.index(top_zhi)
        count = 0
        for i in range(12):
            be = self.ZHI_WUXING[self.ZHI[(start + i) % 12]]
            if self.CONTROLS[be] == element:
                count += 1
        return count

    def _she_hai_select(self, candidates, day_gan):
        cands = self._bi_yong(candidates, day_gan)
        if len(cands) == 1:
            return cands[0], "比用"
        depths = [(l, self._she_hai_depth(l["top"])) for l in cands]
        max_d = max(d for _, d in depths)
        top = [l for l, d in depths if d == max_d]
        if len(top) == 1:
            return top[0], "涉害"
        meng = [l for l in top if l["top"] in self.MENG]
        if meng:
            return meng[0], "涉害(见机)"
        zhong = [l for l in top if l["top"] in self.ZHONG]
        if zhong:
            return zhong[0], "涉害(察微)"
        return top[0], "涉害(季取先)"

    def _is_fuyin(self, shift):
        return shift == 0

    def _is_fanyin(self, heaven_plate_by_earth):
        return all(heaven_plate_by_earth[z] == self.ZHI_CHONG[z] for z in self.ZHI)

    def _select_initial_transmission(self, four_lessons, day_gan, day_zhi,
                                     heaven_plate_by_earth, earth_palace_of_heaven, shift):
        steps = []
        warnings = []
        zei = [l for l in four_lessons if l["relation"] == "下贼上"]
        ke = [l for l in four_lessons if l["relation"] == "上克下"]

        result = {"initial": None, "source_lesson": None, "rule": None, "status": "未实现",
                  "steps": steps, "warnings": warnings,
                  "middle_override": None, "final_override": None}

        if zei or ke:
            if zei:
                if len(zei) == 1:
                    lesson, rule = zei[0], "重审课"
                    steps.append(f"四课中存在唯一一课下贼上：{lesson['name']}。")
                else:
                    lesson, rule = self._she_hai_select(zei, day_gan)
                    steps.append(f"多个下贼上候选，按{rule}取舍。")
            else:
                if len(ke) == 1:
                    lesson, rule = ke[0], "元首课"
                    steps.append(f"四课中无下贼上，存在唯一一课上克下：{lesson['name']}。")
                else:
                    lesson, rule = self._she_hai_select(ke, day_gan)
                    steps.append(f"多个上克下候选，按{rule}取舍。")
            result.update({"initial": lesson["top"], "source_lesson": lesson["index"],
                           "rule": rule, "status": "已确定"})
            steps.append(f"初传 = {lesson['top']}。")
            return result

        # 无克：遥克。
        yao_ke = [l for l in four_lessons
                  if self.CONTROLS[self.ZHI_WUXING[l["top"]]] == self.GAN_WUXING[day_gan]]
        gan_ke = [l for l in four_lessons
                  if self.CONTROLS[self.GAN_WUXING[day_gan]] == self.ZHI_WUXING[l["top"]]]
        if yao_ke:
            lesson, sub_rule = self._she_hai_select(yao_ke, day_gan)
            rule = f"蒿矢课({sub_rule})"
            steps.append("四课无克，上神遥克日干，用蒿矢法。")
            result.update({"initial": lesson["top"], "source_lesson": lesson["index"],
                           "rule": rule, "status": "已确定"})
            steps.append(f"初传 = {lesson['top']}。")
            return result
        if gan_ke:
            lesson, sub_rule = self._she_hai_select(gan_ke, day_gan)
            rule = f"弹射课({sub_rule})"
            steps.append("四课无克，日干遥克上神，用弹射法。")
            result.update({"initial": lesson["top"], "source_lesson": lesson["index"],
                           "rule": rule, "status": "已确定"})
            steps.append(f"初传 = {lesson['top']}。")
            return result

        # 伏吟 / 反吟 / 八专 / 别责 / 昴星。
        if self._is_fuyin(shift):
            yang = self._gan_yinyang(day_gan) == "阳"
            gan_gong = self.JI_GONG[day_gan]
            initial = heaven_plate_by_earth.get(gan_gong if yang else day_zhi)
            rule = "伏吟自任课" if yang else "伏吟自信课"
            steps.append(f"天地盘同位，用{rule}。")
            middle = self.ZHI_XING[initial]
            if middle == initial:
                middle = day_zhi if yang else gan_gong
            final = self.ZHI_XING[middle]
            if final == middle:
                final = self.ZHI_CHONG[middle]
                warnings.append("伏吟末传自刑，取冲支。")
            result.update({"initial": initial, "rule": rule, "status": "已确定",
                           "middle_override": middle, "final_override": final})
            steps.append(f"初传 = {initial}，中传 = {middle}，末传 = {final}。")
            return result

        if self._is_fanyin(heaven_plate_by_earth):
            initial = self.TIANMA_BY_ZHI[day_zhi]
            rule = "反吟井栏射课"
            steps.append("天地盘全冲，四课无克，用井栏射取驿马。")
            result.update({"initial": initial, "rule": rule, "status": "已确定"})
            steps.append(f"初传 = {initial}。")
            return result

        gan_gong = self.JI_GONG[day_gan]
        if day_zhi == gan_gong and (day_gan + day_zhi) in self.BA_ZHUAN_DAYS:
            yang = self._gan_yinyang(day_gan) == "阳"
            base = heaven_plate_by_earth.get(gan_gong)
            target = self.ZHI[(self.ZHI.index(base) + (3 if yang else -3)) % 12]
            initial = heaven_plate_by_earth.get(target)
            rule = "八专课(阳)" if yang else "八专课(阴)"
            steps.append(f"八专日四课不备，按{rule}取传。")
            result.update({"initial": initial, "rule": rule, "status": "已确定"})
            steps.append(f"初传 = {initial}。")
            return result

        if len({l["top"] for l in four_lessons}) == 3:
            if self._gan_yinyang(day_gan) == "阳":
                he_gong = self.JI_GONG[self.WU_HE[day_gan]]
                initial = heaven_plate_by_earth.get(he_gong)
                rule = "别责课(阳)"
            else:
                sanhe = self.SAN_HE[day_zhi]
                qian = sanhe[(sanhe.index(day_zhi) - 1) % 3]
                initial = heaven_plate_by_earth.get(qian)
                rule = "别责课(阴)"
            steps.append(f"四课不备且无克，用{rule}。")
            result.update({"initial": initial, "rule": rule, "status": "已确定"})
            steps.append(f"初传 = {initial}。")
            return result

        # 昴星。
        if self._gan_yinyang(day_gan) == "阳":
            initial = heaven_plate_by_earth.get("酉")
            rule = "昴星虎视课"
            steps.append("四课无克无遥克，阳日取地盘酉上神。")
        else:
            initial = earth_palace_of_heaven.get("酉")
            rule = "昴星冬蛇掩目课"
            steps.append("四课无克无遥克，阴日取天盘酉下神。")
        warnings.append("昴星中末传采用递推规则；该课体中末传存在流派差异。")
        result.update({"initial": initial, "rule": rule, "status": "已确定"})
        steps.append(f"初传 = {initial}。")
        return result

    def _derive_three_transmissions(self, four_lessons, day_gan, day_zhi,
                                    heaven_plate_by_earth, earth_palace_of_heaven,
                                    generals_by_heaven, shift):
        warnings = []
        steps = []
        initial_info = self._select_initial_transmission(
            four_lessons, day_gan, day_zhi,
            heaven_plate_by_earth, earth_palace_of_heaven, shift)
        steps.extend(initial_info["steps"])
        warnings.extend(initial_info["warnings"])
        initial = initial_info["initial"]

        def detail(branch, role):
            if branch is None:
                return None
            return {"branch": branch, "role": role,
                    "general": generals_by_heaven.get(branch),
                    "six_relation": self._six_relation(day_gan, branch)}

        if initial is None:
            return {"initial": None, "middle": None, "final": None,
                    "rule": initial_info["rule"], "status": "未实现",
                    "source_lesson": initial_info["source_lesson"],
                    "derivation_steps": steps, "warnings": warnings,
                    "initial_detail": None, "middle_detail": None, "final_detail": None}

        if initial_info.get("middle_override") is not None:
            middle = initial_info["middle_override"]
            final = initial_info["final_override"]
            steps.append(f"伏吟特殊中末传：中传 = {middle}，末传 = {final}。")
        else:
            middle = heaven_plate_by_earth.get(initial)
            if middle is None:
                warnings.append(f"初传 {initial} 未在地盘支映射中找到，中传无法确定。")
                return {"initial": initial, "middle": None, "final": None,
                        "rule": initial_info["rule"], "status": "部分完成",
                        "source_lesson": initial_info["source_lesson"],
                        "derivation_steps": steps, "warnings": warnings,
                        "initial_detail": detail(initial, "初传"),
                        "middle_detail": None, "final_detail": None}
            steps.append(f"中传 = 地盘 {initial} 上临天盘 {middle}。")
            final = heaven_plate_by_earth.get(middle)
            if final is None:
                warnings.append(f"中传 {middle} 未在地盘支映射中找到，末传无法确定。")
                return {"initial": initial, "middle": middle, "final": None,
                        "rule": initial_info["rule"], "status": "部分完成",
                        "source_lesson": initial_info["source_lesson"],
                        "derivation_steps": steps, "warnings": warnings,
                        "initial_detail": detail(initial, "初传"),
                        "middle_detail": detail(middle, "中传"),
                        "final_detail": None}
            steps.append(f"末传 = 地盘 {middle} 上临天盘 {final}。")

        return {"initial": initial, "middle": middle, "final": final,
                "rule": initial_info["rule"], "status": "已完成",
                "source_lesson": initial_info["source_lesson"],
                "derivation_steps": steps, "warnings": warnings,
                "initial_detail": detail(initial, "初传"),
                "middle_detail": detail(middle, "中传"),
                "final_detail": detail(final, "末传")}

    def _detect_course_type(self, four_lessons, heaven_plate_by_earth, shift):
        if not four_lessons:
            return {"name": "未确定", "status": "未实现", "evidence": [],
                    "warnings": ["四课为空，无法识别课体。"]}
        zei = [l for l in four_lessons if l["relation"] == "下贼上"]
        ke = [l for l in four_lessons if l["relation"] == "上克下"]
        if len(zei) == 1:
            return {"name": "重审课", "status": "已识别", "evidence": {"贼": 1, "克": len(ke)}, "warnings": []}
        if len(ke) == 1 and not zei:
            return {"name": "元首课", "status": "已识别", "evidence": {"贼": 0, "克": 1}, "warnings": []}
        if len(zei) > 1 or len(ke) > 1:
            return {"name": "比用或涉害", "status": "已识别", "evidence": {"贼": len(zei), "克": len(ke)},
                    "warnings": []}
        if self._is_fuyin(shift):
            return {"name": "伏吟", "status": "已识别", "evidence": {"shift": shift}, "warnings": []}
        if self._is_fanyin(heaven_plate_by_earth):
            return {"name": "反吟", "status": "已识别", "evidence": {}, "warnings": []}
        return {"name": "遥克或昴星或别责或八专", "status": "已识别", "evidence": {}, "warnings": []}

    def _build_san_chuan_legacy(self, three_transmissions):
        result = []
        items = [("初传", three_transmissions.get("initial"), three_transmissions.get("initial_detail")),
                 ("中传", three_transmissions.get("middle"), three_transmissions.get("middle_detail")),
                 ("末传", three_transmissions.get("final"), three_transmissions.get("final_detail"))]
        for position, branch, detail in items:
            general = detail.get("general") if detail else None
            relation = detail.get("six_relation", {}).get("relation") if detail else None
            result.append({"pos": position, "position": position, "zhi": branch, "branch": branch,
                           "jiang": general, "general": general, "six_relation": relation,
                           "status": "已计算" if branch is not None else "未实现"})
        return result

    def _build_six_relations(self, day_gan, heaven_plate_by_earth, earth_palace_of_heaven):
        result = {"by_heaven_branch": {}, "by_earth_branch": {}}
        for heaven_branch, earth_branch in earth_palace_of_heaven.items():
            result["by_heaven_branch"][heaven_branch] = {
                **self._six_relation(day_gan, heaven_branch), "earth_palace": earth_branch}
        for earth_branch, heaven_branch in heaven_plate_by_earth.items():
            result["by_earth_branch"][earth_branch] = {
                **self._six_relation(day_gan, heaven_branch), "heaven_branch": heaven_branch}
        return result

    def run(self, yue_jiang, hour_zhi, day_gan, day_zhi, xun_shou=None, xun_kong=None):
        warnings = []
        normalized_yue_jiang = self._normalize_zhi(yue_jiang)
        normalized_hour_zhi = self._normalize_zhi(hour_zhi)
        normalized_day_gan = self._normalize_gan(day_gan)
        normalized_day_zhi = self._normalize_zhi(day_zhi)

        if normalized_yue_jiang is None:
            raise ValueError(f"无效月将：{yue_jiang}")
        if normalized_hour_zhi is None:
            raise ValueError(f"无效时支：{hour_zhi}")
        if normalized_day_gan is None:
            raise ValueError(f"无效日干：{day_gan}")
        if normalized_day_zhi is None:
            raise ValueError(f"无效日支：{day_zhi}")

        heaven_plate_by_earth, earth_palace_of_heaven, shift = self._build_tian_pan(
            normalized_yue_jiang, normalized_hour_zhi)

        four_lessons, lesson_warnings = self._build_four_lessons(
            normalized_day_gan, normalized_day_zhi, heaven_plate_by_earth)
        warnings.extend(lesson_warnings)

        course_type = self._detect_course_type(four_lessons, heaven_plate_by_earth, shift)
        warnings.extend(course_type.get("warnings", []))

        normalized_xun = self._normalize_xun(xun_shou) if xun_shou is not None else None
        if xun_shou is not None and normalized_xun is None:
            warnings.append(f"旬首无效：{xun_shou}")
        calculated_xun_kong = self._get_xun_kong_from_xun(normalized_xun)
        if calculated_xun_kong:
            void_branches = calculated_xun_kong
            if xun_kong is not None:
                supplied = [b for b in self.ZHI if b in xun_kong] if isinstance(xun_kong, str) else list(xun_kong)
                if set(supplied) != set(calculated_xun_kong):
                    warnings.append("传入旬空与旬首计算结果不一致，已采用旬首对应旬空。")
        elif xun_kong is not None:
            void_branches = [b for b in self.ZHI if b in xun_kong] if isinstance(xun_kong, str) else list(xun_kong)
            warnings.append("未提供有效旬首，旬空仅采用外部传入值。")
        else:
            void_branches = []
            warnings.append("未提供有效旬首或旬空，本盘空亡未完成计算。")

        tian_jiang_data = self._get_tian_jiang(
            normalized_day_gan, normalized_hour_zhi, heaven_plate_by_earth)
        warnings.extend(tian_jiang_data.get("warnings", []))
        generals_by_heaven = tian_jiang_data["generals_by_heaven"]
        generals_by_earth = tian_jiang_data["generals_by_earth"]

        six_relations = self._build_six_relations(
            normalized_day_gan, heaven_plate_by_earth, earth_palace_of_heaven)

        three_transmissions = self._derive_three_transmissions(
            four_lessons, normalized_day_gan, normalized_day_zhi,
            heaven_plate_by_earth, earth_palace_of_heaven,
            generals_by_heaven, shift)
        warnings.extend(three_transmissions.get("warnings", []))

        san_chuan = self._build_san_chuan_legacy(three_transmissions)

        sike = []
        for lesson in four_lessons:
            sike.append({"top": lesson["top"], "bottom": lesson["bottom"],
                         "name": lesson["name"], "relation": lesson["relation"],
                         "top_element": lesson.get("top_element"),
                         "bottom_element": lesson.get("bottom_element")})

        plate_rows = {}
        for earth_branch in self.ZHI:
            heaven_branch = heaven_plate_by_earth[earth_branch]
            plate_rows[earth_branch] = {
                "earth_branch": earth_branch,
                "heaven_branch": heaven_branch,
                "earth_palace": earth_branch,
                "heaven_palace": earth_palace_of_heaven.get(heaven_branch),
                "general": generals_by_earth.get(earth_branch),
                "six_relation": self._six_relation(normalized_day_gan, heaven_branch),
                "void": earth_branch in void_branches or heaven_branch in void_branches,
            }

        markers = {
            "day_gan": {"gan": normalized_day_gan,
                        "earth_palace": self.JI_GONG.get(normalized_day_gan),
                        "heaven_branch": heaven_plate_by_earth.get(self.JI_GONG.get(normalized_day_gan))},
            "day_zhi": {"zhi": normalized_day_zhi,
                        "heaven_branch": heaven_plate_by_earth.get(normalized_day_zhi)},
        }

        if course_type["name"] in ("遥克或昴星或别责或八专", "伏吟", "反吟"):
            warnings.append("当前课体属于九宗门中的特殊课体，"
                            "已按本项目采用的主流规则取传，具体流派可能存在差异。")

        warnings.append("六亲为按日干五行与传支五行计算的基础六亲，"
                        "未包含完整神煞、旺衰和课体细分。")

        return {
            "status": "complete" if not warnings else "partial",
            "method": "月将加时；九宗门取传（贼克、比用、涉害、遥克、昴星、别责、八专、伏吟、反吟）。",
            "school": "本项目大六壬规则；特殊课体按主流规则实现，流派差异以 warnings 说明。",
            "yue_jiang": normalized_yue_jiang,
            "hour_zhi": normalized_hour_zhi,
            "day_gan": normalized_day_gan,
            "day_zhi": normalized_day_zhi,
            "xun_shou": normalized_xun,
            "void_branches": void_branches,
            "heaven_plate_by_earth": heaven_plate_by_earth,
            "earth_palace_of_heaven": earth_palace_of_heaven,
            "tian_pan": dict(heaven_plate_by_earth),
            "di_pan": {e: e for e in self.ZHI},
            "generals": {"by_heaven_branch": dict(generals_by_heaven),
                         "by_earth_branch": dict(generals_by_earth),
                         "gui_ren_start": tian_jiang_data.get("gui_ren_start"),
                         "gui_ren_earth": tian_jiang_data.get("gui_ren_earth"),
                         "forward": tian_jiang_data.get("forward")},
            "jiang_pan": dict(generals_by_heaven),
            "four_lessons": four_lessons,
            "sike": sike,
            "course_type": course_type,
            "san_chuan_rule": three_transmissions["rule"],
            "three_transmissions": three_transmissions,
            "san_chuan": san_chuan,
            "six_relations": six_relations,
            "ji_gong": self.JI_GONG.get(normalized_day_gan),
            "markers": markers,
            "plate_rows": plate_rows,
            "rules": {
                "plate_direction": "heaven_plate_by_earth: 地盘支 -> 天盘支",
                "reverse_plate_direction": "earth_palace_of_heaven: 天盘支 -> 地盘支",
                "four_lessons": "一课日干寄宫，二课一课上神，三课日支，四课三课上神",
                "jiu_zong_men": [
                    "贼克（元首/重审）", "比用", "涉害", "遥克（蒿矢/弹射）",
                    "昴星", "别责", "八专", "伏吟", "反吟",
                ],
                "transmission_direction": "除伏吟外，中末传按传支作为地盘支查上神递推。",
            },
            "warnings": warnings,
        }


if __name__ == "__main__":
    import json
    engine = DaLiuRenEngine()
    result = engine.run(yue_jiang="午", hour_zhi="子", day_gan="甲", day_zhi="子", xun_shou="甲子")
    print(json.dumps(result, ensure_ascii=False, indent=2))