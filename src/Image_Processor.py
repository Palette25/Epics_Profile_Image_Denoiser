import os
import cv2
import time
import torch
import numpy as np

from ultralytics import YOLO
from ultralytics.utils import ops
from ultralytics.nn.tasks import  attempt_load_weights

IMAGE_WIDTH = 1440
IMAGE_HEIGHT = 1080

class ImageProcess:
    def __init__(self, model_path):
        # 原始图像尺寸
        self.INPUT_X = IMAGE_WIDTH
        self.INPUT_Y = IMAGE_HEIGHT

        # YOLO检测模型相关的参数定义
        self.model = YOLO(model_path).to('cuda')
        self.INPUT_W, self.INPUT_H = 1088, 1088
        self.class_names = ['edges', 'background', 'light']

    # 图像前处理
    def preprocess_image(self, raw_image):
        # 1. 中值滤波去除背景噪点
        raw_image = cv2.medianBlur(raw_image, 5)
        image = raw_image.copy()
        # 2. 进行图实例分割前预处理
        h, w = image.shape 
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        # Calculate width and height and paddings
        r_w = self.INPUT_W / w
        r_h = self.INPUT_H / h
        if r_h > r_w:
            tw = self.INPUT_W
            th = int(r_w * h)
            tx1 = tx2 = 0
            ty1 = int((self.INPUT_H - th) / 2)
            ty2 = self.INPUT_H - th - ty1
        else:
            tw = int(r_h * w)
            th = self.INPUT_H
            tx1 = int((self.INPUT_W - tw) / 2)
            tx2 = self.INPUT_W - tw - tx1
            ty1 = ty2 = 0
        # Resize the image with long side while maintaining ratio
        image = cv2.resize(image, (tw, th),interpolation=cv2.INTER_LINEAR)

        image = cv2.copyMakeBorder(
            image, ty1, ty2, tx1, tx2, cv2.BORDER_CONSTANT, (114, 114, 114)
        )
        
        image = image.astype(np.float32)   # 7.unit8-->float
        # Normalize to [0,1]
        image /= 255.0    # 8. 逐像素点除255.0
        # HWC to CHW format:
        image = np.transpose(image, [2, 0, 1])
        image = np.expand_dims(image, axis=0)    
        image = np.ascontiguousarray(image)

        return raw_image, image
    
    def remove_padding_and_resize_mask(self, mask, orig_h, orig_w, input_h=1088, input_w=1088):
        """
        mask: numpy array, shape (input_h, input_w)
        orig_h, orig_w: 原图尺寸
        返回：与原图对齐的mask
        """
        # 计算resize和padding参数（与preprocess_image一致）
        r_w = input_w / orig_w
        r_h = input_h / orig_h
        if r_h > r_w:
            tw = input_w
            th = int(r_w * orig_h)
            tx1 = tx2 = 0
            ty1 = int((input_h - th) / 2)
            ty2 = input_h - th - ty1
        else:
            tw = int(r_h * orig_w)
            th = input_h
            tx1 = int((input_w - tw) / 2)
            tx2 = input_w - tw - tx1
            ty1 = ty2 = 0

        # 去除padding
        mask = mask[ty1:input_h-ty2, tx1:input_w-tx2]
        # resize回原图尺寸
        mask = cv2.resize(mask, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)
        return mask

    # 图像后处理，基于实例分割结果对目标类别实例进行mask遮挡
    def postprocess_image(self, raw_image, image, preds):
        # 获取预测结果
        pred = preds[0]
        # 定义返回输出图像
        seg_image = raw_image.copy()

        # 定义目标去除类别
        target_classes = [0, 1]  # 0: edges, 1: background
        orig_h, orig_w = raw_image.shape[:2]

        if pred.masks is not None:
            for mask, cls_id in zip(pred.masks.data.cpu().numpy(), 
                                    pred.boxes.cls.cpu().numpy()):
                # 将掩码转换为二值掩码
                binary_mask = (mask > 0.5).astype(np.uint8) * 255
                # 检查当前类别是否为目标类别
                # 将mask映射回原图尺寸
                aligned_mask = self.remove_padding_and_resize_mask(
                    binary_mask, orig_h, orig_w, self.INPUT_H, self.INPUT_W
                )
                if int(cls_id) in target_classes:
                    seg_image[aligned_mask > 0] = 0
        else:
            print("No masks found in the prediction.")

        return seg_image

    # 整体去噪+检测流程
    def process_image(self, raw_image):
        # 预处理
        raw_image, image = self.preprocess_image(raw_image)

        # 模型推理
        with torch.no_grad():
            preds = self.model(torch.tensor(image))

        # 后处理
        seg_image = self.postprocess_image(raw_image, image, preds)

        return seg_image