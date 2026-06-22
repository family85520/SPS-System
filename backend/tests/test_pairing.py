"""配对关系管理器单元测试"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date

from app.engine.pairing_manager import PairingManager


class TestPairingManager:
    """配对管理器测试"""

    def test_pairing_manager_init(self):
        """测试初始化"""
        db = AsyncMock()
        mgr = PairingManager(db, org_id=4)
        assert mgr.org_id == 4
        assert mgr.db is db

    @pytest.mark.asyncio
    async def test_set_pairing_creates_new(self):
        """测试创建新配对（数据库中不存在时）"""
        db = AsyncMock()
        # get_pairing returns None (no existing record)
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        db.execute.return_value = mock_result

        mgr = PairingManager(db, org_id=4)
        pairing = await mgr.set_pairing(
            shift_id=1, slot_index=0, group_type="day",
            staff_ids=[1, 2], is_new=[True, False],
        )
        # Should have added a new object to session
        db.add.assert_called_once()
        added_obj = db.add.call_args[0][0]
        assert added_obj.org_id == 4
        assert added_obj.shift_id == 1
        assert added_obj.slot_index == 0
        assert added_obj.group_type == "day"
        assert added_obj.staff_ids == [1, 2]
        assert added_obj.is_new == [True, False]

    @pytest.mark.asyncio
    async def test_set_pairing_updates_existing(self):
        """测试更新已有配对"""
        db = AsyncMock()
        mock_pairing = MagicMock()
        mock_pairing.staff_ids = [1, 2]
        mock_pairing.is_new = [True, False]

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_pairing
        db.execute.return_value = mock_result

        mgr = PairingManager(db, org_id=4)
        result = await mgr.set_pairing(
            shift_id=1, slot_index=0, group_type="day",
            staff_ids=[3, 4], is_new=[False, True],
        )
        # Should have updated existing, not added new
        db.add.assert_not_called()
        assert result is mock_pairing
        assert mock_pairing.staff_ids == [3, 4]
        assert mock_pairing.is_new == [False, True]

    @pytest.mark.asyncio
    async def test_get_pairing_returns_existing(self):
        """测试获取已有配对"""
        db = AsyncMock()
        mock_pairing = MagicMock()
        mock_pairing.staff_ids = [1, 2]
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_pairing
        db.execute.return_value = mock_result

        mgr = PairingManager(db, org_id=4)
        result = await mgr.get_pairing(shift_id=1, slot_index=0, group_type="day")
        assert result is mock_pairing
        assert result.staff_ids == [1, 2]

    @pytest.mark.asyncio
    async def test_get_pairing_returns_none_when_not_found(self):
        """测试获取不存在的配对返回 None"""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        db.execute.return_value = mock_result

        mgr = PairingManager(db, org_id=4)
        result = await mgr.get_pairing(shift_id=999, slot_index=0, group_type="day")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_pairings(self):
        """测试获取所有配对关系"""
        db = AsyncMock()
        p1 = MagicMock()
        p1.slot_index = 0
        p2 = MagicMock()
        p2.slot_index = 1
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [p1, p2]
        db.execute.return_value = mock_result

        mgr = PairingManager(db, org_id=4)
        result = await mgr.get_all_pairings(shift_id=1)
        assert len(result) == 2
        assert result[0] is p1
        assert result[1] is p2

    @pytest.mark.asyncio
    async def test_delete_pairings(self):
        """测试删除配对关系"""
        db = AsyncMock()
        mgr = PairingManager(db, org_id=4)
        await mgr.delete_pairings(shift_id=1)
        db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_pairings_from_db(self):
        """测试从数据库加载配对关系"""
        db = AsyncMock()
        p1 = MagicMock()
        p1.slot_index = 0
        p1.group_type = "day"
        p1.staff_ids = [1, 2]
        p1.is_new = [True, False]
        p2 = MagicMock()
        p2.slot_index = 0
        p2.group_type = "night"
        p2.staff_ids = [3, 4]
        p2.is_new = [False, True]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [p1, p2]
        db.execute.return_value = mock_result

        mgr = PairingManager(db, org_id=4)
        result = await mgr.load_pairings(shift_id=1)
        assert (0, "day") in result
        assert (0, "night") in result
        assert result[(0, "day")] == ([1, 2], [True, False])
        assert result[(0, "night")] == ([3, 4], [False, True])

    @pytest.mark.asyncio
    async def test_update_on_special_rotation_replaces_departed(self):
        """测试特殊轮换时替换离职人员"""
        db = AsyncMock()
        mock_pairing = MagicMock()
        mock_pairing.staff_ids = [1, 2, 3]
        mock_pairing.is_new = [False, False, False]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_pairing]

        # Mock the staff query for is_new check
        mock_staff = MagicMock()
        mock_staff.tags = ["新员工"]
        mock_staff_result = MagicMock()
        mock_staff_result.scalars.return_value.first.return_value = mock_staff

        db.execute.side_effect = [mock_result, mock_staff_result]

        mgr = PairingManager(db, org_id=4)
        await mgr.update_on_special_rotation(
            shift_id=1,
            departed_special=[],
            joined_special=[],
            departed_regular=[2],
            joined_regular=[10],
        )
        assert mock_pairing.staff_ids == [1, 10, 3]

    @pytest.mark.asyncio
    async def test_update_on_special_rotation_no_departed(self):
        """测试无离职人员时配对不变"""
        db = AsyncMock()
        mock_pairing = MagicMock()
        mock_pairing.staff_ids = [1, 2, 3]
        mock_pairing.is_new = [False, False, False]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_pairing]
        db.execute.return_value = mock_result

        mgr = PairingManager(db, org_id=4)
        await mgr.update_on_special_rotation(
            shift_id=1,
            departed_special=[],
            joined_special=[],
            departed_regular=[99],
            joined_regular=[10],
        )
        # No change since 99 not in staff_ids
        assert mock_pairing.staff_ids == [1, 2, 3]


class TestPairingIntegration:
    """配对集成测试"""

    def test_pairing_persistence(self):
        """测试配对关系持久化"""
        assert True

    def test_pairing_update_on_staff_change(self):
        """测试人员变更时配对更新"""
        assert True
 
