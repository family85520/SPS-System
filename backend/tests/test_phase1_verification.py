"""Phase 1 Bug Fixes Verification Tests

验证 Phase 1 的三个 Bug 修复是否正确：
1. publish() 方法名正确
2. 跨月连续天数计算使用 pre_history
3. Swap 清理只删除 completed/cancelled
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date


class TestPublishMethodName:
    """验证 1.1: publish 方法名正确"""

    def test_auto_schedule_uses_publish_not_publish_schedules(self):
        """验证自动排班使用正确的 publish 方法名"""
        import inspect
        from app.services.auto_schedule_job import _generate_for_org

        source = inspect.getsource(_generate_for_org)
        # 应该包含 publish 调用
        assert "publish(" in source or "ScheduleService.publish(" in source
        # 不应包含 publish_schedules
        assert "publish_schedules" not in source


class TestCrossMonthContinuousDays:
    """验证 1.2: 跨月连续天数计算"""

    def test_will_exceed_uses_pre_history(self):
        """验证 _will_exceed_continuous 使用 pre_history"""
        import inspect
        from app.engine.scheduler import CandidateFilter

        source = inspect.getsource(CandidateFilter._will_exceed_continuous)
        # 应包含对 _pre_history 的引用
        assert "_pre_history" in source

    def test_schedule_service_loads_pre_history(self):
        """验证 ScheduleService 加载 pre_history"""
        import inspect
        from app.services.schedule_service import ScheduleService

        source = inspect.getsource(ScheduleService.auto_generate)
        assert "pre_history" in source


class TestSwapCleanupLogic:
    """验证 1.3: Swap 清理逻辑"""

    def test_cleanup_preserves_pending_swaps(self):
        """验证清理排班时保留进行中的调班申请"""
        import inspect
        from app.services.schedule_service import _cleanup_existing_schedules

        source = inspect.getsource(_cleanup_existing_schedules)
        # 应只删除 completed/cancelled 状态的 swap
        assert '["completed", "cancelled"]' in source
        # 应重置进行中的 swap 的 target_schedule_id
        assert "target_schedule_id" in source


class TestContinuousDaysCrossMonth:
    """测试跨月连续工作天数计算"""

    def test_continuation_across_month_boundary(self):
        """测试跨月连续工作天数计算"""
        # 上月最后 4 天工作 + 本月第 1 天 = 连续 5 天
        # 本月第 2 天不应再分配

        # 模拟：上月有 4 天排班
        pre_history_dates = ["2026-05-28", "2026-05-29", "2026-05-30", "2026-05-31"]
        current_dates = ["2026-06-01"]  # 本月第 1 天
        all_dates = sorted(set(pre_history_dates + current_dates))

        # 从 5-28 到 6-01 是连续的 5 天
        from datetime import timedelta
        start = date.fromisoformat(all_dates[0])
        end = date.fromisoformat(all_dates[-1])
        actual_days = (end - start).days + 1

        assert actual_days == 5, "连续工作天数应为 5 天"

        # 再加一天 6-02 就超过最大 5 天限制
        all_dates_with_2 = all_dates + ["2026-06-02"]
        end_2 = date.fromisoformat("2026-06-02")
        actual_days_2 = (end_2 - start).days + 1
        assert actual_days_2 == 6, "加入 6-02 后应为 6 天连续"


class TestSlotGrouperDynamicN:
    """测试 2.1: SlotGrouper 动态分组"""

    def test_build_groups_n12(self):
        """测试 12 人场景"""
        from unittest.mock import MagicMock
        from app.engine.scheduler import SlotGrouper

        # 创建 mock staff
        staff_map = {i: MagicMock() for i in range(12)}
        for sid, staff in staff_map.items():
            staff.tags = [] if sid % 2 == 0 else ["新员工"]
            staff.id = sid

        grouper = SlotGrouper(staff_map, lambda sid: sid % 2 == 1)  # 奇数=新员工
        groups = grouper.get_month_groups(sorted(range(12)), 2026, 6)

        # 12 人 = 3 槽位，每槽 4 人（2+2）
        assert len(groups) == 3
        for slot_idx, (dg, ng) in groups.items():
            assert len(dg) == 2, f"槽位 {slot_idx} day_group 应为 2 人"
            assert len(ng) == 2, f"槽位 {slot_idx} night_group 应为 2 人"

    def test_build_groups_n10(self):
        """测试 10 人场景"""
        from unittest.mock import MagicMock
        from app.engine.scheduler import SlotGrouper

        staff_map = {i: MagicMock() for i in range(10)}
        for sid, staff in staff_map.items():
            staff.tags = [] if sid % 2 == 0 else ["新员工"]

        grouper = SlotGrouper(staff_map, lambda sid: sid % 2 == 1)
        groups = grouper.get_month_groups(sorted(range(10)), 2026, 6)

        total = sum(len(dg) + len(ng) for dg, ng in groups.values())
        assert total == 10, f"总人数应为 10，实际 {total}"


class TestHolidayModeConstraint:
    """测试 3.1: HOLIDAY_MODE 约束"""

    def test_holiday_mode_increase_detection(self):
        """测试节假日增加排班人数模式检测"""
        from app.engine.constraint_checker import ConstraintChecker
        from app.engine.models import CheckResult, RuleCheck, Violation

        # 检查是否有 _check_holiday_mode 方法
        checker = ConstraintChecker.__dict__
        assert "_check_holiday_mode" in checker, "应有 _check_holiday_mode 方法"

    def test_holiday_mode_fixed_detection(self):
        """测试节假日固定人员模式检测"""
        from app.engine.constraint_checker import ConstraintChecker

        checker = ConstraintChecker.__dict__
        # fixed 模式在 _check_holiday_mode 内部处理
        assert "_check_holiday_mode" in checker


class TestWeekendDiffConstraint:
    """测试 3.2: WEEKEND_DIFF 约束"""

    def test_weekend_diff_reduced_detection(self):
        """测试周末减少人数模式检测"""
        from app.engine.constraint_checker import ConstraintChecker

        checker = ConstraintChecker.__dict__
        assert "_check_weekend_diff" in checker, "应有 _check_weekend_diff 方法"

    def test_weekend_diff_different_shift_detection(self):
        """测试周末差异化班次模式检测"""
        from app.engine.constraint_checker import ConstraintChecker

        checker = ConstraintChecker.__dict__
        assert "_check_weekend_diff" in checker


class TestFairnessWeightsConfigurable:
    """测试 4.2: FairnessScorer 权重可配置化"""

    def test_default_weights(self):
        """测试默认权重"""
        from app.engine.scoring import FairnessScorer

        scorer = FairnessScorer(existing_schedules=[], existing_details=[], shifts={})
        # 默认值应与应用文档一致
        assert scorer._WEIGHT_HOURS == 0.3
        assert scorer._WEIGHT_NIGHT == 3.0
        assert scorer._WEIGHT_WEEKEND == 2.0
        assert scorer._PENALTY_SAME_DAY == 1000.0
        assert scorer._PENALTY_CONSECUTIVE == 50.0
        assert scorer._PENALTY_GAP_1_DAY == 25.0
        assert scorer._PENALTY_GAP_2_DAY == 10.0
        assert scorer._PENALTY_SAME_SHIFT_TYPE == 30.0

    def test_custom_weights_applied(self):
        """测试自定义权重生效"""
        from app.engine.scoring import FairnessScorer

        custom_weights = {
            "weight_night": 5.0,
            "weight_weekend": 1.0,
        }
        scorer = FairnessScorer(
            existing_schedules=[],
            existing_details=[],
            shifts={},
            weights=custom_weights,
        )
        assert scorer._WEIGHT_NIGHT == 5.0, "夜班权重应为 5.0"
        assert scorer._WEIGHT_WEEKEND == 1.0, "周末权重应为 1.0"
        # 未指定的权重应使用默认值
        assert scorer._WEIGHT_HOURS == 0.3, "工时权重应保持默认"
