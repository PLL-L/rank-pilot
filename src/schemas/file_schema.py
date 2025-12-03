from pydantic import BaseModel, Field, HttpUrl
from typing import Optional

class FileImportRequest(BaseModel):
    file_url: str = Field(..., description="文件下载地址")
    file_name: str = Field(..., max_length=128, description="文件名称")
    function_type: str = Field(..., description="功能模块")
    operation_type: str = Field(..., description="操作类型")
    res_model: str = Field(..., description="关联模型")
    res_id: int = Field(default=None, description="关联ID")
    params: Optional[dict] = Field(default={}, description="额外参数")