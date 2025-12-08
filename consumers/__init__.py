from consumers.file_import.account_import import AccountImport
from consumers.file_import.domain_import import DomainImport
from consumers.file_import.keyword_import import KeywordImport

WORKER_MAP = {
    "domain_import": DomainImport,
    "keyword_import": KeywordImport,
    "account_import": AccountImport,
    # 更多任务类型...
}