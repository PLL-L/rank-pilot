# @Version        : 1.0
# @Update Time    : 2025/4/4 12:55
# @File           : db_mongodb.py
# @IDE            : PyCharm
# @Desc           : MongoDB数据库操作模块

import logging
import asyncio
from typing import Any, Dict, List, Optional, Union, TypeVar, Generic
from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorDatabase,
    AsyncIOMotorCollection,
)
from pymongo.errors import PyMongoError, ConnectionFailure, OperationFailure
from bson import ObjectId
from starlette.requests import Request
from functools import wraps

from src.core import logger, settings
from src.utils.singleton import Singleton

T = TypeVar("T")


def handle_mongo_errors(func):
    """MongoDB操作错误处理装饰器"""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ConnectionFailure as e:
            logger.error(f"MongoDB连接错误: {str(e)}")
            raise
        except OperationFailure as e:
            logger.error(f"MongoDB操作错误: {str(e)}")
            raise
        except PyMongoError as e:
            logger.error(f"MongoDB错误: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"未知错误: {str(e)}")
            raise

    return wrapper


class AsyncMongoManager(metaclass=Singleton):
    """MongoDB连接管理器（单例模式）"""

    _client: Optional[AsyncIOMotorClient] = None
    _default_db: str = "test_db"
    _connection_attempts: int = 3
    _retry_delay: float = 1.0

    def __init__(self, uri: str = None, default_db: str = None, **client_kwargs: Any):
        """
        初始化MongoDB连接池

        Args:
            uri: MongoDB连接URI
            default_db: 默认数据库名称
            client_kwargs: Motor客户端额外参数
        """
        if self.__class__._client is not None:
            return

        if not uri:
            uri = settings.db.MONGO_DB.MONGO_DB_URL.unicode_string()

        # 设置默认连接池参数
        pool_kwargs = {
            "maxPoolSize": 100,
            "minPoolSize": 10,
            "connectTimeoutMS": 5000,
            "socketTimeoutMS": 30000,
            "waitQueueTimeoutMS": 10000,
            "retryWrites": True,
            "retryReads": True,
            **client_kwargs,
        }

        self.__class__._client = AsyncIOMotorClient(uri, **pool_kwargs)
        self.__class__._default_db = default_db or settings.db.MONGO_DB.MONGO_DB_ENABLE
        logger.info("🐍 MONGODB engine initialized 🐍 ")

    @handle_mongo_errors
    async def ping(self) -> bool:
        """检查数据库连接状态"""
        for attempt in range(self._connection_attempts):
            try:
                await self._client.admin.command("ping")
                return True
            except PyMongoError as e:
                if attempt == self._connection_attempts - 1:
                    logger.error(f"MongoDB连接失败: {str(e)}")
                    return False
                await asyncio.sleep(self._retry_delay)
        return False

    def get_database(self, db_name: Optional[str] = None) -> AsyncIOMotorDatabase:
        """获取数据库实例"""
        return self.__class__._client[db_name or self.__class__._default_db]

    def get_collection(
        self, collection_name: str, db_name: Optional[str] = None
    ) -> AsyncIOMotorCollection:
        """获取集合实例"""
        return self.get_database(db_name)[collection_name]

    @handle_mongo_errors
    async def close(self) -> None:
        """关闭数据库连接"""
        if self.__class__._client:
            self.__class__._client.close()
            self.__class__._client = None

    @handle_mongo_errors
    async def close_pool(self) -> None:
        """安全关闭整个连接池"""
        if self.__class__._client:
            self.__class__._client.close()
            self.__class__._client = None
            self.__class__._default_db = "test_db"
            logger.info("MongoDB连接池关闭成功")

    def get_pool_stats(self) -> Dict[str, Any]:
        """获取连接池实时状态信息"""
        if not self.__class__._client:
            return {"status": "disconnected"}

        try:
            pool = self.__class__._client._get_connection()
            active_connections = len(pool.active_connections)
            idle_connections = len(pool.idle_connections)
            total_connections = active_connections + idle_connections
            usage_rate = (
                active_connections / self.__class__._client.max_pool_size
            ) * 100

            stats = {
                "status": "connected",
                "max_pool_size": self.__class__._client.max_pool_size,
                "min_pool_size": self.__class__._client.min_pool_size,
                "active_connections": active_connections,
                "idle_connections": idle_connections,
                "total_connections": total_connections,
                "usage_rate": f"{usage_rate:.1f}%",
            }

            logger.info(
                f"连接池状态 | "
                f"最大:{stats['max_pool_size']} "
                f"活跃:{stats['active_connections']} "
                f"空闲:{stats['idle_connections']} "
                f"使用率:{stats['usage_rate']}"
            )
            return stats
        except AttributeError as e:
            logger.error(f"获取连接池状态失败: {str(e)}")
            return {"status": "unknown"}

    @classmethod
    async def shutdown(cls):
        """安全关闭的类方法形式"""
        instance = cls()
        await instance.close_pool()


class AsyncMongoDAO(Generic[T]):
    """MongoDB数据访问对象"""

    def __init__(
        self,
        manager: AsyncMongoManager,
        default_collection: str,
        default_db: Optional[str] = None,
    ):
        """
        初始化DAO

        Args:
            manager: 连接管理器实例
            default_collection: 默认集合名称
            default_db: 默认数据库名称
        """
        self.manager = manager
        self.default_db = default_db
        self.default_collection = default_collection

    @handle_mongo_errors
    async def insert_one(
        self,
        document: Dict[str, Any],
        collection_name: Optional[str] = None,
        db_name: Optional[str] = None,
    ) -> str:
        """插入单个文档"""
        coll = self._get_collection(collection_name, db_name)
        result = await coll.insert_one(document)
        return str(result.inserted_id)

    @handle_mongo_errors
    async def find_one(
        self,
        query: Dict[str, Any],
        collection_name: Optional[str] = None,
        db_name: Optional[str] = None,
        projection: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """查询单个文档"""
        coll = self._get_collection(collection_name, db_name)
        document = await coll.find_one(query, projection)
        return self._convert_objectid(document)

    @handle_mongo_errors
    async def find(
        self,
        query: Dict[str, Any],
        collection_name: Optional[str] = None,
        db_name: Optional[str] = None,
        projection: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 0,
        sort: Optional[List[tuple]] = None,
    ) -> List[Dict[str, Any]]:
        """查询多个文档"""
        coll = self._get_collection(collection_name, db_name)
        cursor = coll.find(query, projection)

        if sort:
            cursor = cursor.sort(sort)
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)

        results = await cursor.to_list(length=None)
        return self._convert_objectid(results)

    @handle_mongo_errors
    async def update_one(
        self,
        query: Dict[str, Any],
        update: Dict[str, Any],
        collection_name: Optional[str] = None,
        db_name: Optional[str] = None,
        upsert: bool = False,
    ) -> bool:
        """更新单个文档"""
        coll = self._get_collection(collection_name, db_name)
        result = await coll.update_one(query, update, upsert=upsert)
        return result.modified_count > 0

    @handle_mongo_errors
    async def delete_one(
        self,
        query: Dict[str, Any],
        collection_name: Optional[str] = None,
        db_name: Optional[str] = None,
    ) -> bool:
        """删除单个文档"""
        coll = self._get_collection(collection_name, db_name)
        result = await coll.delete_one(query)
        return result.deleted_count > 0

    @handle_mongo_errors
    async def count_documents(
        self,
        query: Dict[str, Any],
        collection_name: Optional[str] = None,
        db_name: Optional[str] = None,
    ) -> int:
        """统计文档数量"""
        coll = self._get_collection(collection_name, db_name)
        return await coll.count_documents(query)

    def _get_collection(
        self, collection_name: Optional[str] = None, db_name: Optional[str] = None
    ) -> AsyncIOMotorCollection:
        """获取集合实例"""
        return self.manager.get_collection(
            collection_name=collection_name or self.default_collection,
            db_name=db_name or self.default_db,
        )

    @staticmethod
    def _convert_objectid(data: Any) -> Any:
        """转换ObjectId为字符串"""
        if isinstance(data, list):
            return [AsyncMongoDAO._convert_objectid(item) for item in data]
        if isinstance(data, dict):
            if "_id" in data and isinstance(data["_id"], ObjectId):
                data["_id"] = str(data["_id"])
            for key, value in data.items():
                data[key] = AsyncMongoDAO._convert_objectid(value)
        return data


# FastAPI依赖注入函数
def get_mongo_database(db_name: Optional[str] = None):
    """获取数据库实例的依赖函数"""

    async def get_database(request: Request):
        return request.app.state.mongo_manager.get_database(db_name)

    return get_database


def get_mongo_collection(collection_name: str, db_name: Optional[str] = None):
    """获取集合实例的依赖函数"""

    async def get_collection(request: Request):
        return request.app.state.mongo_manager.get_collection(collection_name, db_name)

    return get_collection


# --------------------------
# 使用示例
# --------------------------
async def main():
    # 初始化连接管理器
    mongo_manager = AsyncMongoManager(
        uri="mongodb://localhost:27017",
        default_db="test_db",
        maxPoolSize=100,
        minPoolSize=10,
    )

    # 初始化DAO实例
    user_dao = AsyncMongoDAO(
        manager=mongo_manager, default_collection="users", default_db="test_db"
    )

    try:
        # 检查连接状态
        if not await mongo_manager.ping():
            raise ConnectionError("MongoDB connection failed")

        # 插入数据
        user_id = await user_dao.insert_one(
            {"username": "john_doe", "email": "john@example.com"}
        )
        print(f"Inserted user ID: {user_id}")

        # 查询数据
        user = await user_dao.find_one({"username": "john_doe"})
        print(f"Found user: {user}")

    except Exception as e:
        logging.error(f"Operation failed: {str(e)}")
    finally:
        await mongo_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
