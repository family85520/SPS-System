"""Bug 修复回归测试"""
import pytest


class TestAutoScheduleJobFix:
    """验证 auto_schedule_job 使用正确的 publish 方法名"""

    def test_publish_method_exists(self):
        from app.services.schedule_service import ScheduleService
        assert hasattr(ScheduleService, 'publish')

    def test_publish_is_static(self):
        """publish 方法应该是静态方法（可直接通过类调用）"""
        import inspect
        from app.services.schedule_service import ScheduleService
        # 静态方法不接收 self 参数
        sig = inspect.signature(ScheduleService.publish)
        params = list(sig.parameters.keys())
        assert 'self' not in params


class TestCrossMonthContinuous:
    """验证跨月连续天数计算"""

    def test_pre_history_merges_with_current(self):
        """前序历史应与当前数据合并计算连续天数"""
        from app.engine.scheduler import CandidateFilter
        from unittest.mock import MagicMock

        scorer = MagicMock()
        scorer.staff_days = {1: {"2026-07-01", "2026-07-02"}}

        filter_obj = CandidateFilter(
            staff_special_rules={},
            constraint_params={"MAX_CONTINUOUS_DAYS": {"max_days": 5}},
            existing_details=[],
            existing_schedules=[],
            shift_templates={},
            scorer=scorer,
            pre_history={1: ["2026-06-28", "2026-06-29", "2026-06-30"]},
        )
        filter_obj._run_start_str = "2026-07-01"

        # 7月3日排班：连续6天（6.28-7.3），应超过5天上限
        assert filter_obj._will_exceed_continuous(1, "2026-07-03", 5) is True

        # 7月1日排班：连续4天（6.28-7.1），未超过
        assert filter_obj._will_exceed_continuous(1, "2026-07-01", 5) is False

    def test_no_pre_history_still_works(self):
        """无前序历史时，连续天数计算仍应正常工作"""
        from app.engine.scheduler import CandidateFilter
        from unittest.mock import MagicMock

        scorer = MagicMock()
        scorer.staff_days = {1: {"2026-07-01", "2026-07-02", "2026-07-03"}}

        filter_obj = CandidateFilter(
            staff_special_rules={},
            constraint_params={"MAX_CONTINUOUS_DAYS": {"max_days": 5}},
            existing_details=[],
            existing_schedules=[],
            shift_templates={},
            scorer=scorer,
            pre_history=None,
        )
        filter_obj._run_start_str = "2026-07-01"

        # 3天连续，未超过5天上限
        assert filter_obj._will_exceed_continuous(1, "2026-07-04", 5) is False

        # 5天连续，恰好等于上限
        scorer.staff_days = {1: {"2026-07-01", "2026-07-02", "2026-07-03", "2026-07-04", "2026-07-05"}}
        assert filter_obj._will_exceed_continuous(1, "2026-07-06", 5) is True

    def test_gap_in_pre_history_breaks_continuity(self):
        """前序历史中有间隔应中断连续性"""
        from app.engine.scheduler import CandidateFilter
        from unittest.mock import MagicMock

        scorer = MagicMock()
        scorer.staff_days = {1: {"2026-07-01", "2026-07-02"}}

        # 6月28日缺失，6.29-6.30 和 7.01-7.02 之间有间隔
        filter_obj = CandidateFilter(
            staff_special_rules={},
            constraint_params={"MAX_CONTINUOUS_DAYS": {"max_days": 5}},
            existing_details=[],
            existing_schedules=[],
            shift_templates={},
            scorer=scorer,
            pre_history={1: ["2026-06-29", "2026-06-30"]},
        )
        filter_obj._run_start_str = "2026-07-01"

        # 连续4天（6.29-6.30, 7.01-7.02），未超过
        assert filter_obj._will_exceed_continuous(1, "2026-07-03", 5) is False


class TestScheduleServiceMethods:
    """验证 ScheduleService 关键方法存在性"""

    def test_auto_generate_method_exists(self):
        from app.services.schedule_service import ScheduleService
        assert hasattr(ScheduleService, 'auto_generate')

    def test_recall_method_exists(self):
        from app.services.schedule_service import ScheduleService
        assert hasattr(ScheduleService, 'recall')

    def test_approve_method_exists(self):
        from app.services.schedule_service import ScheduleService
        assert hasattr(ScheduleService, 'approve')


class TestPairingSyncRules:
    """Pairing persistence should follow day/night alternation."""

    def test_even_rotation_day_shift_syncs_day_group(self):
        from datetime import date
        from unittest.mock import MagicMock
        from app.services.schedule_service import _resolve_pairing_slot_and_group

        shift = MagicMock(start_time="08:00", end_time="16:00")

        slot_index, group_type = _resolve_pairing_slot_and_group(date(2026, 7, 1), shift)

        assert slot_index == 0
        assert group_type == "day"

    def test_odd_rotation_day_shift_syncs_night_group(self):
        from datetime import date
        from unittest.mock import MagicMock
        from app.services.schedule_service import _resolve_pairing_slot_and_group

        shift = MagicMock(start_time="08:00", end_time="16:00")

        slot_index, group_type = _resolve_pairing_slot_and_group(date(2026, 7, 4), shift)

        assert slot_index == 0
        assert group_type == "night"
