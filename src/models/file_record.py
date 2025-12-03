from typing import Optional, Any, Dict
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, String, Text, Integer
from sqlalchemy.dialects.postgresql import JSONB  # 针对PG的JSONB支持
from src.models.mixins import CommonMixin


class FileRecordBase(SQLModel):
    file_name: str = Field(sa_column=Column(String(128), nullable=False, comment="文件名称"))
    file_url: str = Field(sa_column=Column(String(255), nullable=False, comment="文件地址"))
    res_model: str = Field(sa_column=Column(String(64), nullable=True, comment="关联的资源模型/表"))
    res_id: Optional[int] = Field(default=None, sa_column=Column(Integer, nullable=True, comment="关联的资源ID"))

    # 状态建议使用枚举，这里先用String匹配需求
    status: str = Field(
        default="process",
        sa_column=Column(String(64),nullable=False, comment="任务状态: process, fail, success, cancel")
    )

    operation_type: str = Field(sa_column=Column(String(64), nullable=True, comment="操作类型: 1.export 2.import"))
    function_type: str = Field(sa_column=Column(String(64), nullable=True, comment="功能模块"))

    remark: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True, comment="备注"))
    params: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB, nullable=True, comment="JSONB 参数"))




class FileRecordTable(CommonMixin, FileRecordBase, table=True):
    __tablename__ = "file_record"