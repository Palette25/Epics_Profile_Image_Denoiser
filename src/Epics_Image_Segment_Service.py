#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 图像去噪主程序

import os
import cv2
import time
import yaml
import torch
import epics
import numpy as np
import matplotlib.pyplot as plt
from threading import Thread
from queue import Queue  # 引入队列

# 自定义模块
import Image_Processor
from utils.utils import *

# 读取全局配置参数
config_file = open('../config/config.yaml')
config = yaml.safe_load(config_file)
# 从配置文件中读取参数
IMAGE_PV_NAME = config['PV_CONFIG']['IMAGE_PV_NAME']
RESULT_PV_NAME = config['PV_CONFIG']['RESULT_PV_NAME']
IMAGE_SIZE = config['PV_CONFIG']['IMAGE_SIZE']
YOLO_MODEL_PATH = config['ENVIRON_CONFIG']['YOLO_MODEL_PATH']
EPICS_CA_MAX_ARRAY_BYTES = config['ENVIRON_CONFIG']['EPICS_CA_MAX_ARRAY_BYTES']
CUDA_VISIBLE_DEVICES = config['ENVIRON_CONFIG']['CUDA_VISIBLE_DEVICES']

# 设置环境变量
# 设置 EPICS 最大数组字节数
os.environ["EPICS_CA_MAX_ARRAY_BYTES"] = EPICS_CA_MAX_ARRAY_BYTES
# 指定使用第0号GPU
os.environ["CUDA_VISIBLE_DEVICES"] = CUDA_VISIBLE_DEVICES 

# 定义 EPICS PV 名称
IMAGE_PV_NAME = IMAGE_PV_NAME  # 替换为实际的图像 PV 名称
RESULT_PV_NAME = RESULT_PV_NAME  # 替换为实际的结果 PV 名称
RESULT_PV = epics.PV(RESULT_PV_NAME) #  结果PV对象

# 创建任务队列
task_queue = Queue()

def process_task_queue():
    """
    从队列中按顺序处理任务。
    """
    while True:
        try:
            # 从队列中获取任务
            start_time_1 = time.time()
            image_array = task_queue.get()
            if image_array is None:
                break  # 如果收到 None，退出线程
            # 打印队列取数耗时
            print(f"[Debug] 队列取数耗时: {time.time() - start_time_1:.2f}s")

            # 模型推理
            start_time_2 = time.time()
            processed_image = image_detector.process_image(image_array)
            # 打印模型推理耗时
            print(f"[Debug] 模型推理耗时: {time.time() - start_time_2:.2f}s")

            # 发送处理后的结果到结果 PV
            start_time_3 = time.time()
            send_result_to_pv(RESULT_PV_NAME, RESULT_PV, processed_image)
            print(f"[Info] 处理后的图像已发送到 PV: {RESULT_PV_NAME}")
            # 打印PV写入耗时
            print(f"[Debug] PV写入耗时: {time.time() - start_time_3:.2f}s")
            # 打印整体处理耗时
            print(f"[Debug] 整体处理耗时: {time.time() - start_time_1:.2f}s")

        except Exception as e:
            print(f"[Error] 处理任务时出错: {e}")
        finally:
            task_queue.task_done()  # 标记任务完成

# 原始Profile图像更新时的回调函数
def on_image_update(pvname=None, value=None, **kwargs):
    """
    PV 值更新时的回调函数。
    """
    print(f"[Info] PV {pvname} 触发更新回调")
    if value is None:
        print(f"[Warning] PV {pvname} 的值为空，跳过处理")
        return

    try:
        # 将 PV 数据转换为图像
        image_array = np.array(value, dtype=np.uint8).reshape(IMAGE_HEIGHT, IMAGE_WIDTH)
        print(f"[Info] 从 PV {pvname} 获取到新图像数据，形状: {image_array.shape}")

        # 将任务放入队列
        task_queue.put(image_array)

    except Exception as e:
        print(f"[Error] 处理 PV {pvname} 数据时出错: {e}")

# 主函数
if __name__ == "__main__":
    # 读取图像分割模型
    model_path = r'./model/best.pt'
    image_detector = Image_Processor.ImageProcess(model_path)

    print('[Running Device] ' + str(image_detector.model.device))

    # 启动任务处理线程
    worker_thread = Thread(target=process_task_queue, daemon=True)
    worker_thread.start()

    try:
        # camonitor机制监控图像PV
        monitor_image_pv(IMAGE_PV_NAME, on_image_update)

        while True:
            time.sleep(0.001)  # 主线程保持运行

    except KeyboardInterrupt:
        print("[Info] 用户中断，程序退出")
    except Exception as e:
        print("[Error] " + str(e))
    finally:
        # 向队列发送 None，通知线程退出
        task_queue.put(None)
        worker_thread.join()
        # 关闭文件
        config_file.close()
        print("===== Shutting Down =====")