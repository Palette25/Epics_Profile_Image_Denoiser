import os
import cv2
import time
import numpy as np

from pcaspy import SimpleServer, Driver

# Set environment variables for EPICS
os.environ['EPICS_CA_MAX_ARRAY_BYTES'] = '20971520'

IMAGE_SIZE = 1080*1440
RESULT_SIZE = 1080*1440

image_src_path = r'D:\YOLO11\images\random_UD-BI_PRF7_RAW_ArrayData_YAG_last300.npy_81.png'

image_array = cv2.imread(image_src_path, cv2.IMREAD_GRAYSCALE).flatten().astype(np.uint8)

# 定义轮换图像路径数组
image_paths = [
    r'D:\YOLO11\images\random_UD-BI_PRF7_RAW_ArrayData_YAG_last300.npy_81.png',
    r'D:\YOLO11\images\random_UD-BI_PRF8_RAW_ArrayData_YAG.npy_44.png',
    r'D:\YOLO11\images\random_UD-BI_PRF9_RAW_ArrayData_YAG.npy_87.png'
]

# 当前图像下标
current_image_index = 0

prefix = 'TEST:'
pvdb = {
    'IMAGE': {
        'type': 'int',
        'count': IMAGE_SIZE,
        'value': image_array,
        'desc': 'CCD Image Array',
        'unit': 'counts'
    },
    'RES_IMAGE': {
        'type': 'int',
        'count': RESULT_SIZE,
        'value': np.zeros(RESULT_SIZE, dtype=np.uint8),
        'desc': 'CCD Result Image Array',
        'unit': 'counts'
    }
}

class myDriver(Driver):
    def __init__(self):
        super(myDriver, self).__init__()

    def read(self, reason):
        value = self.getParam(reason)
        # print(f"Read {reason} = {value}")

        return value

    def write(self, reason, value):
        # check value length
        if len(value) != RESULT_SIZE:
            print("ERROR: Array length must be 1440*1080")
            return False
        
        # print(f"Write {reason} = {value}")
        self.setParam(reason, np.array(value, dtype=np.uint8))

        return True

# 主程序
if __name__ == '__main__':
    server = SimpleServer()
    server.createPV(prefix, pvdb)

    driver = myDriver()

    print("===== 模拟Epics PV服务器环境 =====")
    print("===== 启动成功 =====")

    # 定义上次更新的时间
    last_update_time = time.time()

    try:
        while True:
            # 当前时间
            current_time = time.time()

            # 检查是否需要更新 PV
            if current_time - last_update_time >= 0.2:  # 每隔 n 秒更新一次 # 200ms -- 20Hz
                image_array = cv2.imread(image_paths[current_image_index], cv2.IMREAD_GRAYSCALE).flatten().astype(np.uint8)
                driver.setParam('IMAGE', image_array)
                driver.updatePVs()

                # 更新图像下标
                current_image_index = (current_image_index + 1) % len(image_paths)

                # 更新上次更新时间
                last_update_time = current_time

            # 快速处理客户端请求
            server.process(0)  # 保持较小的阻塞时间
    except KeyboardInterrupt:
        print("--Shutting Down--")