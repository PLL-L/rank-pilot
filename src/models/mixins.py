from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, TIMESTAMP, text


class TimestampMixin(SQLModel, table=False):
    """
    时间戳 Mixin，提供 id、created_at、updated_at 字段
    
    注意：由于 SQLModel 的限制，无法在 Mixin 中同时满足：
    1. 使用 BigInteger 类型作为主键
    2. 使用 TIMESTAMP 和 server_default
    3. 让 model_dump() 能够序列化这些字段
    
    解决方案：在 Response Schema 的 from_db_model 方法中使用 model_validate(orm_object)
    而不是 model_validate(orm_object.model_dump())，这样可以从 ORM 对象的属性读取值。
    """
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)

