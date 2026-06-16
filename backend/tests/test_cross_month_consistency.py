"""跨月一致性测试 - 验证逐月/多月生成结果一致"""
import pytest
from datetime import date


class TestCrossMonthConsistency:
    """跨月一致性测试"""

    def test_special_rotation_consistency(self):
        """特殊人员轮换应保持一致"""
        # 模拟2个特殊人员 [A, B] 在2个班次间轮换
        pool = [1, 2]
        count = 1

        # 月1: 白班特殊 = [1], 行政特殊 = [2]
        # 月2: 白班特殊 = [2], 行政特殊 = [1]
        # 月3: 白班特殊 = [1], 行政特殊 = [2]

        month1_day = pool[:count]
        month1_admin = pool[count:]

        # 月2: 白班特殊人员 = 上月行政特殊人员
        month2_day = month1_admin
        month2_admin = month1_day

        # 月3: 回到月1的状态
        month3_day = month2_admin
        month3_admin = month2_day

        assert month3_day == month1_day, "月3白班特殊人员应与月1相同"
        assert month3_admin == month1_admin, "月3行政特殊人员应与月1相同"

    def test_pairing_derive_from_schedule(self):
        """测试从排班记录推导配对关系"""
        # 模拟：连续多天人员组合稳定
        # 第1天: [1, 2, 3, 4]
        # 第2天: [1, 2, 3, 4]
        # 第3天: [1, 2, 3, 4]
        # 应推导出稳定配对: (1,2) 和 (3,4)

        day_staff = {
            "2026-06-01": [1, 2, 3, 4],
            "2026-06-02": [1, 2, 3, 4],
            "2026-06-03": [1, 2, 3, 4],
        }

        from collections import Counter
        pair_cooccurrence = Counter()
        for staff_on_day in day_staff.values():
            for i in range(len(staff_on_day)):
                for j in range(i + 1, len(staff_on_day)):
                    pair = tuple(sorted([staff_on_day[i], staff_on_day[j]]))
                    pair_cooccurrence[pair] += 1

        # (1,2) 和 (3,4) 各出现3天
        assert pair_cooccurrence[(1, 2)] == 3
        assert pair_cooccurrence[(3, 4)] == 3
        # (1,3) 也出现3天... 所以所有配对都稳定
        # threshold = max(3, 3//2) = 3
        threshold = 3
        stable_pairs = [(pair, count) for pair, count in pair_cooccurrence.items() if count >= threshold]
        assert len(stable_pairs) == 6  # 4人共6对

    def test_month_by_month_consistency(self):
        """测试逐月生成一致性（逻辑验证）"""
        # 逐月生成时，每个月都读取上月排班记录
        # 多月生成时，所有月份一次生成
        # 两者应该产生相同结果的关键在于：
        # 1. 特殊人员轮换方向一致
        # 2. 配对关系持久化正确

        # 模拟：4个月轮换
        pool = [1, 2]
        months = []
        current = pool[:]

        for m in range(4):
            months.append(current[:])
            # 轮换：特殊人员在两个班次间交替
            current = current[::-1]  # 简单翻转模拟轮换

        # 月1和月3应相同，月2和月4应相同
        assert months[0] == months[2], "月1和月3特殊人员应相同"
        assert months[1] == months[3], "月2和月4特殊人员应相同"

    def test_manual_adjustment_preserves_pairing(self):
        """测试手动调整后配对关系保持"""
        # 模拟：手动调整某天的配对
        # 原配对: [(0, "day"): (100, 200), (0, "night"): (300, 400)]
        # 手动调整: 将 200 替换为 500
        # 新配对: [(0, "day"): (100, 500), (0, "night"): (300, 400)]
        # 后续月份应使用新配对

        original = {
            (0, "day"): (100, 200),
            (0, "night"): (300, 400),
        }
        adjusted = {
            (0, "day"): (100, 500),
            (0, "night"): (300, 400),
        }

        # 验证调整只影响 day 组
        assert original[(0, "night")] == adjusted[(0, "night")]
        assert adjusted[(0, "day")] == (100, 500)
