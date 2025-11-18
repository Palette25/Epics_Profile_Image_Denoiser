@echo off

chcp 65001 > nul
color 07

echo ===== Profile图像增强可视化软件 =====
echo ===== 启动成功 =====
echo ===== 输出日志路径：./logging/vis.log =====

cd ./visualization/

call conda activate yolo

python py_vis.py

echo ====== 可视化软件退出 ======