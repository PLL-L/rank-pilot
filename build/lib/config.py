"""
应用配置设置
支持从环境变量和.env文件加载配置
"""
import os
import secrets
from ipaddress import IPv4Address
from pathlib import Path
from typing import Union, List
from urllib.parse import quote_plus

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource, YamlConfigSettingsSource
from pydantic import RedisDsn, MongoDsn, Field, field_validator, computed_field

root_path: Path = Path(__file__).resolve().parents[1]

class RedisConfig(BaseSettings):
    """Redis配置

    Attributes:
        REDIS_USERNAME: Redis用户名
        REDIS_PASSWORD: Redis密码
        REDIS_HOST: Redis主机地址
        REDIS_PORT: Redis端口
        REDIS_DB: Redis数据库编号
        REDIS_DB_ENABLE: 是否启用Redis
    """

    REDIS_USERNAME: str = Field(default="", description="Redis用户名")
    REDIS_PASSWORD: str = Field(default="", description="Redis密码")
    REDIS_HOST: str = Field(default="127.0.0.1", description="Redis主机地址")
    REDIS_PORT: int = Field(default=6379, description="Redis端口")
    REDIS_DB: int = Field(default=0, description="Redis数据库编号")
    REDIS_DB_ENABLE: bool = Field(default=False, description="是否启用Redis")


    @computed_field
    @property
    def REDIS_DB_URL(self) -> RedisDsn:
        """Redis连接URL"""
        return RedisDsn.build(
            scheme="redis",
            host=self.REDIS_HOST,
            port=self.REDIS_PORT,
            path=f"/{self.REDIS_DB}",
            username=self.REDIS_USERNAME,
            password=self.REDIS_PASSWORD,
        )


class MongoConfig(BaseSettings):
    """MongoDB配置

    Attributes:
        MONGO_DB_ENABLE: 是否启用MongoDB
        MONGO_DB_URL: MongoDB连接URL
        MONGO_DB_NAME: MongoDB数据库名称
    """

    MONGO_DB_ENABLE: bool = Field(default=False, description="是否启用MongoDB")
    MONGO_DB_URL: MongoDsn = Field(default="mongodb://root:xxxx@127.0.0.1:27017/", description="MongoDB连接URL")
    MONGO_DB_NAME: str = Field(default="test", description="MongoDB数据库名称")


class DataBaseSettings(BaseSettings):
    """数据库基础配置

    Attributes:
        DB_USERNAME: 数据库用户名
        DB_PASSWORD: 数据库密码
        DB_HOST: 数据库主机地址
        DB_PORT: 数据库端口
        DB_NAME: 数据库名称
    """

    DB_USERNAME: str = Field(default="root", description="数据库用户名")
    DB_PASSWORD: str = Field(default="aa1234bb", description="数据库密码")
    DB_SCHEMA: str = Field(default="mysql+aiomysql", description="数据库Schema")
    DB_HOST: str = Field(default="127.0.0.1", description="数据库主机地址")
    DB_PORT: int = Field(default=3306, description="数据库端口")
    DB_NAME: str = Field(default="test", description="数据库名称")
    DB_ECHO: bool = Field(default=False, description="是否输出SQL语句")

    POOL_SIZE: int = Field(default=5, description="连接池大小")
    MAX_OVERFLOW: int = Field(default=10, description="")# todo
    POOL_TIMEOUT: int = Field(default=60, description="")# todo
    POOL_RECYCLE: int = Field(default=3600, description="")# todo
    POOL_PRE_PING: bool = Field(default=True, description="")# todo
    POOL_RESET_ON_RETURN: bool = Field(default=True, description="")# todo
    ECHO_POOL: bool = Field(default=False, description="")# todo

    @computed_field
    @property
    def DB_URL(self) -> str:
        """数据库连接URL"""
        return f"{self.DB_SCHEMA}://{quote_plus(self.DB_USERNAME)}:{quote_plus(self.DB_PASSWORD)}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"



class DBSettings(BaseSettings):
    """数据库配置

    Attributes:
        ORM_DB: ORM配置
        REDIS_DB: Redis配置
        MONGO_DB: MongoDB配置
    """
    ORM_DB: DataBaseSettings = Field(default_factory=DataBaseSettings, description="ORM配置")
    REDIS_DB: RedisConfig = Field(default_factory=RedisConfig, description="Redis配置")
    MONGO_DB: MongoConfig = Field(default_factory=MongoConfig, description="MongoDB配置")

class SystemSettings(BaseSettings):
    """系统配置

    Attributes:
        DEBUG: FAST API 是否开启调试模式
        LOG_CONSOLE_OUT: 是否输出日志到控制台
        LOG_PATH: 日志路径
        CORS_ORIGIN_ENABLE: 是否启用CORS
        ALLOW_ORIGINS: 允许的源
        ALLOW_CREDENTIALS: 是否允许凭证
        ALLOW_METHODS: 允许的方法
        ALLOW_HEADERS: 允许的头部
        MAX_ATTEMPTS: 最大尝试次数
        DESENSITIZE_FIELDS: 数据脱敏
        API_V1_STR: API 版本
    """

    DEBUG: bool = Field(default=False, description="是否开启调试模式")
    # 日志等级
    LOG_LEVEL: str = Field(default="DEBUG", description="日志等级")
    LOG_CONSOLE_OUT: bool = Field(default=True, description="是否输出日志到控制台")
    LOG_PATH: str = Field(
        default=os.path.join(root_path, "logs"), description="日志路径"
    )

    CORS_ORIGIN_ENABLE: bool = Field(default=True, description="是否启用CORS")
    ALLOW_ORIGINS: List[str] = Field(default=["*"], description="允许的源")
    ALLOW_CREDENTIALS: bool = Field(default=True, description="是否允许凭证")
    ALLOW_METHODS: List[str] = Field(default=["*"], description="允许的方法")
    ALLOW_HEADERS: List[str] = Field(default=["*"], description="允许的头部")



    API_V1_STR: str = Field(
        default="/api/v1",
        description="API V1前缀"
    )

    RANK_ZEN_TRACE_ID: str = Field(
        default="X-Request-ID",
        description="rank-zen的trace id"
    )

    MAX_ATTEMPTS: int = Field(default=5, description="最大尝试次数")
    DESENSITIZE_FIELDS: List[str] = Field(
        default=["password", "old_password", "new_password", "phone"],
        description="脱敏字段",
    )


    @field_validator(
        "LOG_PATH",
    )
    def validate_paths(cls, v: str) -> str:
        """验证路径是否存在，不存在则创建"""
        os.makedirs(v, exist_ok=True)
        return v

    @field_validator("LOG_LEVEL")
    def validate_log_level(cls, v: str) -> str:
        """确保日志级别为大写"""
        return v.upper()

class FastAPISettings(BaseSettings):
    """FastAPI配置

    Attributes:
        TITLE: API标题
        DESCRIPTION: API描述
        HOST: 监听主机
        PORT: 监听端口
        VERSION: API版本
    """

    TITLE: str = Field(default="src-admin", description="API标题")
    DESCRIPTION: str = Field(default="", description="API描述")
    HOST: IPv4Address = Field(default="0.0.0.0", description="监听主机")
    PORT: int = Field(default=9000, description="监听端口")
    VERSION: str = Field(default="1.0.0", description="API版本")


class RabbitMQSettings(BaseSettings):

    # rabbitmq settings
    RABBITMQ_URL: str = Field(
        "amqp://ksherpay:ksherpay@mq@112.74.105.10:5672/",  description="RabbitMQ 连接地址"
    )
    RABBITMQ_EXCHANGE_NAME: str = Field(
        f"rank_zen_exchange_{os.getenv("APP_ENV")}", description="RabbitMQ 交换机"
    )
    RABBITMQ_EXCHANGE_TYPE: str = Field("direct", description="RabbitMQ 交换机类型")
    RABBITMQ_DISABLE_LOGGING: bool = Field(False, alias="RABBITMQ_DISABLE_LOGGING")



class Settings(BaseSettings):
    """
    应用设置类
    配置优先级: 环境变量 > .env文件 > 默认值
    
    用法:
        # 环境变量示例
        export PROJECT_NAME="My API"
        export DATABASE_URL="mysql+pymysql://user:pass@localhost/dbname"
        
        # 或者在.env文件中配置
        PROJECT_NAME=My API
        DATABASE_URL=mysql+pymysql://user:pass@localhost/dbname
    """

    db: DBSettings = Field(default_factory=DBSettings, description="数据库配置")
    system: SystemSettings = Field(default_factory=SystemSettings,description="系统配置")
    FASTAPI_CONFIG: FastAPISettings = Field(default_factory=FastAPISettings, description="FastAPI配置")
    RABBITMQ_CONFIG: RabbitMQSettings = Field(default_factory=RabbitMQSettings, description="FastAPI配置")



    model_config = SettingsConfigDict(
        extra="ignore",
        yaml_file=os.path.join(
            root_path,"config", f"{os.getenv('APP_ENV', default='dev')}.yaml"
        ),
        yaml_file_encoding="utf-8",
    )


    # 加载环境变量优先级
    @classmethod
    def settings_customise_sources(
            cls,
            settings_cls: type[BaseSettings],
            init_settings: PydanticBaseSettingsSource,
            env_settings: PydanticBaseSettingsSource,
            dotenv_settings: PydanticBaseSettingsSource,
            file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """自定义配置源

        Returns:
            tuple[PydanticBaseSettingsSource, ...]: 配置源元组
        """
        return (
            init_settings,
            env_settings,
            YamlConfigSettingsSource(settings_cls),
        )


# 创建设置实例
settings = Settings()


if __name__ == "__main__":
    pass
