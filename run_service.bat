@echo off

echo ===== Profile图像增强在线服务 =====
echo ===== 启动成功 =====

cd ./src/

call conda activate yolo

python Epics_Image_Segment_Service.py

pause