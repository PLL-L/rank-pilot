from enum import Enum


class PlatformName:
    """
    平台枚举
    """
    BAIDU = "BAIDU"
    S360 = "360"


class AccountStatus(str, Enum):
    """
    账号状态枚举
    """
    INIT = "init"
    NORMAL = "normal"
    LOGIN_FAILED = "login_failed"



class TerminalTypeEnum(str, Enum):
    """
    终端类型枚举
    """
    PC = "PC"
    MOBILE = "MOBILE"


class BusinessTypeEnum(str, Enum):
    """
    终端类型枚举
    """
    KEYWORD = "keyword"
    HOT_PAGE = "hot_page"