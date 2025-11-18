#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 多线程EPICS图像去噪服务（单GPU环境）

import os
import time
import yaml
import epics
import logging
import numpy as np
from queue import Queue
import threading
import Image_Processor
from utils.utils import *

# 读取全局配置参数
config_path = '../config/config.yaml'
with open(config_path, 'r', encoding='utf-8') as config_file:
    config = yaml.safe_load(config_file)

IMAGE_WIDTH = config['PV_CONFIG']['IMAGE_WIDTH']
IMAGE_HEIGHT = config['PV_CONFIG']['IMAGE_HEIGHT']
YOLO_MODEL_PATH = config['ENVIRON_CONFIG']['YOLO_MODEL_PATH']
EPICS_CA_MAX_ARRAY_BYTES = config['ENVIRON_CONFIG']['EPICS_CA_MAX_ARRAY_BYTES']
CUDA_VISIBLE_DEVICES = config['ENVIRON_CONFIG']['CUDA_VISIBLE_DEVICES']

os.environ["EPICS_CA_MAX_ARRAY_BYTES"] = EPICS_CA_MAX_ARRAY_BYTES
os.environ["CUDA_VISIBLE_DEVICES"] = CUDA_VISIBLE_DEVICES

# PV列表分组
pv_groups = [
    ("INJ", config['PV_CONFIG']['INJ_PROFILE_IMAGE_PVS'], config['PV_CONFIG']['INJ_PROFILE_SEG_IMAGE_PVS']),
    ("COL", config['PV_CONFIG']['COL_PROFILE_IMAGE_PVS'], config['PV_CONFIG']['COL_PROFILE_SEG_IMAGE_PVS']),
    ("DIAG0", config['PV_CONFIG']['DIAG0_PROFILE_IMAGE_PVS'], config['PV_CONFIG']['DIAG0_PROFILE_SEG_IMAGE_PVS']),
    ("DIAG1", config['PV_CONFIG']['DIAG1_PROFILE_IMAGE_PVS'], config['PV_CONFIG']['DIAG1_PROFILE_SEG_IMAGE_PVS']),
]

# 统一任务队列
task_queue = Queue()
NUM_WORKERS = 4  # 可根据GPU性能调整

# 只加载一次模型
image_detector = Image_Processor.ImageProcess(YOLO_MODEL_PATH)

# 为每个PV创建独立Logger
pv_loggers = {}

def get_logger_for_pv(pvname):
    if pvname in pv_loggers:
        return pv_loggers[pvname]
    logger = logging.getLogger(f"service_{pvname}")
    logger.setLevel(logging.INFO)
    log_dir = "../logging"
    os.makedirs(log_dir, exist_ok=True)
    # 定义不同PV量对应的日志文件路径
    log_file_name = f"service_{pvname}.log".replace(":", "_")
    log_file = os.path.join(log_dir, log_file_name)
    # 检查log_file是否存在，若不存在则创建
    if not os.path.exists(log_file):
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("")  # 创建空文件

    fh = logging.FileHandler(log_file, encoding='utf-8')
    fmt = logging.Formatter('%(asctime)s %(message)s')
    fh.setFormatter(fmt)
    # 防止重复添加handler
    if not logger.handlers:
        logger.addHandler(fh)
    pv_loggers[pvname] = logger
    return logger

def process_task():
    while True:
        item = task_queue.get()
        if item is None:
            break
        pvname, value, result_pv_name = item
        logger = get_logger_for_pv(pvname)
        try:
            image_array = np.array(value, dtype=np.uint8).reshape(IMAGE_HEIGHT, IMAGE_WIDTH)
            processed_image, preprocess_time, inference_time, postprocess_time = image_detector.process_image(image_array)
            result_pv = epics.PV(result_pv_name)
            result_pv.put(processed_image.flatten(), wait=True)
            logger.info(f"[Info] {pvname} -> {result_pv_name} 完成推理并写入PV")
        except Exception as e:
            logger.error(f"[Error] 处理 {pvname} 数据时出错: {e}")
        finally:
            task_queue.task_done()

def on_image_update_factory(image_pv_name, result_pv_name):
    logger = get_logger_for_pv(image_pv_name)
    def on_image_update(pvname=None, value=None, **kwargs):
        if value is None:
            logger.warning(f"[Warning] PV {pvname} 的值为空，跳过处理")
            return
        task_queue.put((image_pv_name, value, result_pv_name))
        logger.info(f"[Info] PV {pvname} 收到新数据，已加入任务队列")
    return on_image_update

if __name__ == "__main__":
    # 启动后台工作线程
    workers = []
    for _ in range(NUM_WORKERS):
        t = threading.Thread(target=process_task, daemon=True)
        t.start()
        workers.append(t)

    # 注册所有PV监控
    for group_name, image_pvs, result_pvs in pv_groups:
        for image_pv, result_pv in zip(image_pvs, result_pvs):
            monitor_image_pv(image_pv, on_image_update_factory(image_pv, result_pv))
            logger = get_logger_for_pv(image_pv)
            logger.info(f"[Main] 注册PV监控: {group_name} {image_pv} -> {result_pv}")

    try:
        logging.info(f"[Main] 服务已启动，工作线程数: {NUM_WORKERS}。按Ctrl+C退出。")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("[Main] 收到中断信号，正在关闭服务...")
        for _ in range(NUM_WORKERS):
            task_queue.put(None)
        for t in workers:
            t.join()
        logging.info("[Main] 所有工作线程已关闭。")