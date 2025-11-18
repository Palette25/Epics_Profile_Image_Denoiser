@echo off

chcp 65001 > nul
color 07

echo ===== Profile图像增强在线服务 =====
echo ===== 同时监控PV量数目：26 =====
echo ===== 启动成功 =====
echo ===== 输出日志路径：./logging/service.log =====

cd ./src/

call conda activate yolo

python MT_Epics_Image_Segment_Service.py

echo ====== 在线服务退出 ======