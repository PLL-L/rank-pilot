# #!/usr/bin/python
# # -*- coding: utf-8 -*-
# # @Version        : 1.0
# # @Update Time    : 2024/12/5 23:41
# # @File           : qiniu_file.py
# # @IDE            : PyCharm
# # @Desc           : 七牛云文件上传策略
#
# import os
# from typing import Optional, List
# from fastapi import UploadFile
# from qiniu import Auth, put_file, put_data
# from src.config import settings
# from src.core.exception import BaseAppException
# from src.utils.file.base import AbstractUpload
#
#
# class QiniuFileStrategy(AbstractUpload):
#     """七牛云文件上传策略
#
#     使用七牛云作为文件存储服务，支持图片、视频、音频等文件的上传和删除。
#
#     Attributes:
#         access_key: 七牛云 AccessKey
#         secret_key: 七牛云 SecretKey
#         bucket_name: 存储空间名称
#         domain: 七牛云域名
#     """
#
#     def __init__(self):
#         """初始化七牛云上传策略"""
#         self.access_key = settings.qiniu.ACCESS_KEY
#         self.secret_key = settings.qiniu.SECRET_KEY
#         self.bucket_name = settings.qiniu.BUCKET_NAME
#         self.domain = settings.qiniu.DOMAIN
#         self.auth = Auth(self.access_key, self.secret_key)
#
#     async def upload_video(
#         self,
#         path: str,
#         file: UploadFile,
#         accept: Optional[List[str]] = None,
#         max_size: int = 5,
#     ) -> str:
#         """上传视频文件到七牛云
#
#         Args:
#             path: 保存路径
#             file: 上传的文件
#             accept: 允许的文件类型列表
#             max_size: 最大文件大小(MB)
#
#         Returns:
#             str: 文件访问URL
#
#         Raises:
#             BaseAppException: 上传失败时抛出
#         """
#         # 验证文件
#         self.validate_file(file, max_size, accept or self.VIDEO_ACCEPT)
#
#         # 生成文件路径
#         file_path = self.generate_relative_path(path, file.filename)
#
#         try:
#             # 读取文件内容
#             content = await file.read()
#
#             # 生成上传凭证
#             token = self.auth.upload_token(self.bucket_name, file_path)
#
#             # 上传文件
#             ret, info = put_data(token, file_path, content)
#
#             if ret and ret.get("key") == file_path:
#                 return f"{self.domain}/{file_path}"
#             else:
#                 raise BaseAppException(msg=f"上传失败: {info.error}")
#
#         except Exception as e:
#             raise BaseAppException(msg=f"上传失败: {str(e)}")
#         finally:
#             await file.close()
#
#     async def upload_image(
#         self,
#         path: str,
#         file: UploadFile,
#         accept: Optional[List[str]] = None,
#         max_size: int = 5,
#     ) -> str:
#         """上传图片文件到七牛云
#
#         Args:
#             path: 保存路径
#             file: 上传的文件
#             accept: 允许的文件类型列表
#             max_size: 最大文件大小(MB)
#
#         Returns:
#             str: 文件访问URL
#
#         Raises:
#             BaseAppException: 上传失败时抛出
#         """
#         # 验证文件
#         self.validate_file(file, max_size, accept or self.IMAGE_ACCEPT)
#
#         # 生成文件路径
#         file_path = self.generate_relative_path(path, file.filename)
#
#         try:
#             # 读取文件内容
#             content = await file.read()
#
#             # 生成上传凭证
#             token = self.auth.upload_token(self.bucket_name, file_path)
#
#             # 上传文件
#             ret, info = put_data(token, file_path, content)
#
#             if ret and ret.get("key") == file_path:
#                 return f"{self.domain}/{file_path}"
#             else:
#                 raise BaseAppException(msg=f"上传失败: {info.error}")
#
#         except Exception as e:
#             raise BaseAppException(msg=f"上传失败: {str(e)}")
#         finally:
#             await file.close()
#
#     async def upload_file(
#         self,
#         path: str,
#         file: UploadFile,
#         accept: Optional[List[str]] = None,
#         max_size: int = 5,
#     ) -> str:
#         """上传普通文件到七牛云
#
#         Args:
#             path: 保存路径
#             file: 上传的文件
#             accept: 允许的文件类型列表
#             max_size: 最大文件大小(MB)
#
#         Returns:
#             str: 文件访问URL
#
#         Raises:
#             BaseAppException: 上传失败时抛出
#         """
#         # 验证文件
#         self.validate_file(file, max_size, accept or self.FILE_ACCEPT)
#
#         # 生成文件路径
#         file_path = self.generate_relative_path(path, file.filename)
#
#         try:
#             # 读取文件内容
#             content = await file.read()
#
#             # 生成上传凭证
#             token = self.auth.upload_token(self.bucket_name, file_path)
#
#             # 上传文件
#             ret, info = put_data(token, file_path, content)
#
#             if ret and ret.get("key") == file_path:
#                 return f"{self.domain}/{file_path}"
#             else:
#                 raise BaseAppException(msg=f"上传失败: {info.error}")
#
#         except Exception as e:
#             raise BaseAppException(msg=f"上传失败: {str(e)}")
#         finally:
#             await file.close()
#
#     async def upload_audio(
#         self,
#         path: str,
#         file: UploadFile,
#         accept: Optional[List[str]] = None,
#         max_size: int = 5,
#     ) -> str:
#         """上传音频文件到七牛云
#
#         Args:
#             path: 保存路径
#             file: 上传的文件
#             accept: 允许的文件类型列表
#             max_size: 最大文件大小(MB)
#
#         Returns:
#             str: 文件访问URL
#
#         Raises:
#             BaseAppException: 上传失败时抛出
#         """
#         # 验证文件
#         self.validate_file(file, max_size, accept or self.AUDIO_ACCEPT)
#
#         # 生成文件路径
#         file_path = self.generate_relative_path(path, file.filename)
#
#         try:
#             # 读取文件内容
#             content = await file.read()
#
#             # 生成上传凭证
#             token = self.auth.upload_token(self.bucket_name, file_path)
#
#             # 上传文件
#             ret, info = put_data(token, file_path, content)
#
#             if ret and ret.get("key") == file_path:
#                 return f"{self.domain}/{file_path}"
#             else:
#                 raise BaseAppException(msg=f"上传失败: {info.error}")
#
#         except Exception as e:
#             raise BaseAppException(msg=f"上传失败: {str(e)}")
#         finally:
#             await file.close()
#
#     async def delete_file(self, path: str) -> bool:
#         """从七牛云删除文件
#
#         Args:
#             path: 文件路径
#
#         Returns:
#             bool: 删除是否成功
#
#         Raises:
#             BaseAppException: 删除失败时抛出
#         """
#         try:
#             from qiniu import BucketManager
#
#             bucket = BucketManager(self.auth)
#
#             # 从完整URL中提取文件路径
#             if path.startswith(self.domain):
#                 path = path[len(self.domain) + 1 :]
#
#             # 删除文件
#             ret, info = bucket.delete(self.bucket_name, path)
#
#             if info.status_code == 200:
#                 return True
#             else:
#                 raise BaseAppException(msg=f"删除失败: {info.error}")
#
#         except Exception as e:
#             raise BaseAppException(msg=f"删除失败: {str(e)}")
