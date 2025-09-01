@echo off

echo ===== Profile图像增强可视化软件 =====
echo ===== 启动成功 =====

cd ./visualization/

call conda activate yolo

python py_vis.py
