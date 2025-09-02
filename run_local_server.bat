@echo off

cd ./local_server/

call conda activate yolo

python Epics_Server.py

pause