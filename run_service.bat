@echo off

echo ===== Profile图像增强在线服务 =====
echo ===== 启动成功 =====
echo ===== 输出日志路径：./logging/service.log =====

cd ./src/

call conda activate yolo

python Epics_Image_Segment_Service.py

echo ===== 在线服务退出 =====

pause