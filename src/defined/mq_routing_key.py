import os

from src.config import settings


class MqRoutingKey:
    TEST_QUEUE = f"test_queue_{settings.system.RUN_MODE}".lower()
    FILE_IMPORT = f"file_export_{settings.system.RUN_MODE}".lower()
