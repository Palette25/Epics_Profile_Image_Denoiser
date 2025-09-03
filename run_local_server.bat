@echo off

echo ===== 本地Epics服务器 =====
echo ===== 启动成功 =====

cd ./local_server/

call conda activate yolo

python Epics_Server.py

echo ===== 本地Epics服务器退出 =====
pause