"""导出模板模型"""

from sqlalchemy import String, LargeBinary, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer as SaInteger
from app.database import Base
from app.models.base import TimestampMixin


class ExportTemplate(Base, TimestampMixin):
    """自定义导出模板表"""
    __tablename__ = "exp_export_template"

    id: Mapped[int] = mapped_column(SaInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="模板名称")
    file_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, comment="模板文件(.xlsx)")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否默认模板")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="模板说明")
