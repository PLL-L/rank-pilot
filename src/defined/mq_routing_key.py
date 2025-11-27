import os


class MqRoutingKey:
    TEST_QUEUE = f"test_queue_{os.getenv("APP_ENV")}"
