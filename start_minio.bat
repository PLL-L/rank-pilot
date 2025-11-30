@echo off
chcp 65001 >nul 2>&1
echo 正在启动MinIO容器...

:: 1. 先检查容器是否已存在，存在则停止并删除
docker ps -a | findstr /i "minio" >nul
if %errorlevel% equ 0 (
    echo 发现已存在minio容器，先停止并删除...
    docker stop minio >nul
    docker rm minio >nul
)

:: 2. 创建Windows本地数据目录（按需修改路径）
set "MINIO_DATA_DIR=E:\minio"
if not exist "%MINIO_DATA_DIR%" (
    mkdir "%MINIO_DATA_DIR%"
    echo 已创建本地数据目录：%MINIO_DATA_DIR%
)

:: 3. 启动MinIO容器（核心命令）
docker run ^
--name minio ^
-p 9000:9000 ^
-p 9090:9090 ^
-d ^
-e "MINIO_ROOT_USER=admin" ^
-e "MINIO_ROOT_PASSWORD=aa1234bb" ^
-v "%MINIO_DATA_DIR%:/data" ^
minio/minio:RELEASE.2025-03-12T18-04-18Z server /data --console-address ":9090" --address ":9000"

:: 4. 验证启动结果
if %errorlevel% equ 0 (
    echo MinIO容器启动成功！
    echo 控制台地址：http://localhost:9090
    echo API地址：http://localhost:9000
    echo 账号：admin  密码：aa1234bb
) else (
    echo 错误：MinIO容器启动失败，请检查Docker是否运行！
    pause
)