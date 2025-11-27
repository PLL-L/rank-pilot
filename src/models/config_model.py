from enum import Enum
from sqlalchemy import Column, String
from sqlmodel import SQLModel, Field

from src.models.mixins import TimestampMixin


class ConfigType(str, Enum):
    RUNNING = "running"
    USER = "user"
    SYSTEM = "system"


class ConfigBase(SQLModel):
    config_name: str = Field(sa_column=Column(String(128), nullable=False))
    config_type: ConfigType | None = Field(default=None, sa_column=Column(String(16), nullable=True))
    config_key: str = Field(sa_column=Column(String(128), nullable=False))
    config_value: str = Field(sa_column=Column(String(256), nullable=False))
    remark: str | None = Field(default=None, sa_column=Column(String(128), nullable=True))

class ConfigTable(TimestampMixin, ConfigBase, table=True):
    __tablename__ = "zen_config"



