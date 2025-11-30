import re
from datetime import datetime
from typing import Optional

from pydantic import field_validator
from sqlalchemy import Column, String, TIMESTAMP, text, Integer, Boolean
from sqlmodel import SQLModel, Field

from src.models.mixins import TimestampMixin


class DomainBase(SQLModel):
    """域名信息基础模型"""
    domain_name: Optional[str] = Field(
        min_length=1,
        max_length=255,
        sa_column=Column(String(255), nullable=False, comment="域名信息"),
        description="用户录入的域名信息，前后去空格，需要校验域名的合法性"
    )
    main_domain: Optional[str] = Field(
        default=None,
        max_length=255,
        sa_column=Column(String(255), nullable=True, comment="主域名"),
        description="自动根据域名计算出来的主域名"
    )
    domain_group: Optional[str] = Field(
        default=None,
        max_length=16,
        sa_column=Column(String(16), nullable=True, comment="域名分组"),
        description="用户自定义的域名分组信息，不超过16个字符"
    )
    server_number: Optional[str] = Field(
        default=None,
        max_length=16,
        sa_column=Column(String(16), nullable=True, comment="服务器ID"),
        description="所在服务器信息，用户录入的字符串信息，不超过16个字符"
    )
    remark: Optional[str] = Field(
        default=None,
        max_length=64,
        sa_column=Column(String(64), nullable=True, comment="备注信息"),
        description="用户的备注信息，不超过64个字符"
    )
    baidu_site_account: Optional[str] = Field(
        default=None,
        max_length=32,
        sa_column=Column(String(32), nullable=True, comment="百度站平号"),
        description="百度站长平台账号名，不超过32个字符，站平账号检查时主动上传，上传后实时更新"
    )
    is_baidu_verified: Optional[bool] = Field(
        default=None,
        sa_column=Column(Boolean, nullable=True, comment="是否通过百度认证"),
        description="是否通过百度站长平台认证"
    )
    baidu_token: Optional[str] = Field(
        default=None,
        max_length=32,
        sa_column=Column(String(32), nullable=True, comment="百度站长token"),
        description="百度站长平台token，不超过32个字符，站平账号检查时主动上传"
    )
    created_uid: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, nullable=True, comment="创建人ID"),
        description="创建该记录的用户ID"
    )
    updated_uid: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, nullable=True, comment="更新人ID"),
        description="最后更新该记录的用户ID"
    )

    @field_validator('domain_name')
    @classmethod
    def validate_and_clean_domain(cls, v: str) -> str:
        """验证域名合法性并去除前后空格"""
        if not v:
            raise ValueError('域名不能为空')

        # 去除前后空格并转换为小写（域名不区分大小写）
        domain = v.strip().lower()

        if not domain:
            raise ValueError('域名不能为空')

        # 检查是否为punycode码（xn--开头）
        if domain.startswith('xn--'):
            raise ValueError('不支持punycode码，请使用中文域名作为请求参数')

        # 分离域名主体和后缀
        if '.' not in domain:
            raise ValueError('域名必须包含顶级域名后缀')

        domain_parts = domain.rsplit('.', 1)
        domain_body = domain_parts[0]  # 域名主体
        tld = domain_parts[1]  # 顶级域名

        # 验证域名主体长度（1-63个字符）
        if len(domain_body) < 1 or len(domain_body) > 63:
            raise ValueError('域名主体长度必须为1-63个字符')

        # 检查是否包含中文（简体或繁体）
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', domain_body))

        if has_chinese:
            # 中文域名验证
            cls._validate_chinese_domain(domain_body)
        else:
            # 英文域名验证
            cls._validate_english_domain(domain_body)

        # 验证顶级域名（至少2个字母）
        if not re.match(r'^[a-zA-Z]{2,}$', tld):
            raise ValueError('顶级域名格式不合法')

        return domain

    @classmethod
    def _validate_english_domain(cls, domain_body: str) -> None:
        """验证英文域名"""
        # 英文域名合法字符：a-z、0-9、短划线（-）
        if not re.match(r'^[a-z0-9-]+$', domain_body):
            raise ValueError('英文域名只能包含字母、数字和短划线')

        # 短划线不能出现在开头和结尾
        if domain_body.startswith('-') or domain_body.endswith('-'):
            raise ValueError('短划线不能出现在域名开头或结尾')

        # 短划线不能同时在第三和第四字符位置
        if len(domain_body) >= 4:
            if domain_body[2] == '-' and domain_body[3] == '-':
                raise ValueError('短划线不能同时在第三和第四字符位置')

    @classmethod
    def _validate_chinese_domain(cls, domain_body: str) -> None:
        """验证中文域名"""
        # 中文域名必须含有至少一个汉字
        if not re.search(r'[\u4e00-\u9fff]', domain_body):
            raise ValueError('中文域名必须包含至少一个汉字')

        # 中文域名合法字符：中文、a-z、0-9、短划线（-）
        if not re.match(r'^[\u4e00-\u9fff a-z0-9-]+$', domain_body):
            raise ValueError('中文域名只能包含中文、字母、数字和短划线')

        # 短划线不能出现在开头和结尾
        if domain_body.startswith('-') or domain_body.endswith('-'):
            raise ValueError('短划线不能出现在域名开头或结尾')

        # 短划线不能同时在第三和第四字符位置
        if len(domain_body) >= 4:
            if domain_body[2] == '-' and domain_body[3] == '-':
                raise ValueError('短划线不能同时在第三和第四字符位置')

    @field_validator('domain_group')
    @classmethod
    def validate_domain_group(cls, v: Optional[str]) -> Optional[str]:
        """验证域名分组长度"""
        if v is not None:
            v = v.strip()
            if len(v) > 16:
                raise ValueError('域名分组不能超过16个字符')
        return v

    @field_validator('server_number')
    @classmethod
    def validate_server_id(cls, v: Optional[str]) -> Optional[str]:
        """验证服务器ID长度"""
        if v is not None:
            v = v.strip()
            if len(v) > 16:
                raise ValueError('服务器ID不能超过16个字符')
        return v

    @field_validator('remark')
    @classmethod
    def validate_remark(cls, v: Optional[str]) -> Optional[str]:
        """验证备注信息长度"""
        if v is not None:
            v = v.strip()
            if len(v) > 64:
                raise ValueError('备注信息不能超过64个字符')
        return v

    @field_validator('baidu_site_account')
    @classmethod
    def validate_baidu_site_account(cls, v: Optional[str]) -> Optional[str]:
        """验证百度站平号长度"""
        if v is not None:
            v = v.strip()
            if len(v) > 32:
                raise ValueError('百度站平号不能超过32个字符')
        return v

    @field_validator('baidu_token')
    @classmethod
    def validate_baidu_token(cls, v: Optional[str]) -> Optional[str]:
        """验证百度站长token长度"""
        if v is not None:
            v = v.strip()
            if len(v) > 32:
                raise ValueError('百度站长token不能超过32个字符')
        return v


class DomainTable(TimestampMixin,DomainBase, table=True):
    """域名信息表模型"""
    __tablename__ = "domain_info"
    id: Optional[int] = Field(default=None, primary_key=True)

    def __init__(self, **data):
        super().__init__(**data)
        # 自动计算主域名
        if self.domain_name and not self.main_domain:
            self.main_domain = self._extract_main_domain(self.domain_name)

    @staticmethod
    def _extract_main_domain(domain: str) -> str:
        """从域名中提取主域名"""
        try:
            # 简单的主域名提取逻辑
            # 例如：api.example.com -> example.com
            parts = domain.split('.')
            if len(parts) >= 2:
                # 取最后两个部分作为主域名
                return '.'.join(parts[-2:])
            return domain
        except Exception:
            return domain