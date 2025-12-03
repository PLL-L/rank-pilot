# 1. 定义一个同步操作函数（使用普通的 Session API）
from typing import Type




def run_bulk_update_sync(sync_session, model_class: Type, update_info: list):
    # 它拥有 bulk_update_mappings 方法
    sync_session.bulk_update_mappings(
        model_class,
        update_info
    )
