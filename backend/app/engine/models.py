"""约束校验引擎内部数据模型"""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Violation:
    """违规记录"""
    rule_type: str          # 违反的规则类型
    rule_name: str          # 规则名称
    message: str            # 违规描述
    schedule_id: int        # 相关排班记录ID
    staff_id: int           # 相关人员ID
    date: str               # 相关日期
    severity: str           # warning / error


@dataclass
class RuleCheck:
    """单条规则检查结果"""
    rule_type: str
    rule_name: str
    passed: bool
    message: str = ""


@dataclass
class CheckResult:
    """全局校验结果"""
    passed: list[RuleCheck] = field(default_factory=list)
    warnings: list[Violation] = field(default_factory=list)
    failed: list[Violation] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.failed) == 0

    @property
    def passed_count(self) -> int:
        return len(self.passed)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    @property
    def failed_count(self) -> int:
        return len(self.failed)

    def to_dict(self) -> dict:
        return {
            "passed_count": self.passed_count,
            "warning_count": self.warning_count,
            "failed_count": self.failed_count,
            "is_valid": self.is_valid,
            "passed": [
                {"rule_type": r.rule_type, "rule_name": r.rule_name, "message": r.message}
                for r in self.passed
            ],
            "warnings": [
                {
                    "rule_type": v.rule_type,
                    "rule_name": v.rule_name,
                    "message": v.message,
                    "schedule_id": v.schedule_id,
                    "staff_id": v.staff_id,
                    "date": v.date,
                    "severity": v.severity,
                }
                for v in self.warnings
            ],
            "failed": [
                {
                    "rule_type": v.rule_type,
                    "rule_name": v.rule_name,
                    "message": v.message,
                    "schedule_id": v.schedule_id,
                    "staff_id": v.staff_id,
                    "date": v.date,
                    "severity": v.severity,
                }
                for v in self.failed
            ],
        }
