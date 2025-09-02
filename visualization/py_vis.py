# 软件运行界面
import sys
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, 
                             QVBoxLayout, QHBoxLayout, QGroupBox, QStatusBar,
                             QTableWidget, QTableWidgetItem, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap, QColor
import epics

# 图像尺寸常量
IMAGE_WIDTH = 1440
IMAGE_HEIGHT = 1080

# 定义EPICS PV名称
PV1_NAME = 'TEST:IMAGE'       # 替换为实际的图像
PV2_NAME = 'TEST:RES_IMAGE'   # 替换为实际的结果图像

class ImageDisplayWidget(QLabel):
    """用于显示图像的QLabel子类"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setText("等待图像数据...")
        self.setMinimumSize(800, 600)
        
    def set_image(self, image_data):
        """将numpy数组转换为QImage并显示"""
        if image_data is None or image_data.size == 0:
            self.setText("无有效图像数据")
            return
            
        # 确保图像数据是二维的
        if len(image_data.shape) != 2:
            self.setText("无效的图像数据维度")
            return
            
        # 归一化图像数据到0-255范围
        image_data_uint8 = image_data.astype(np.uint8)
        
        # 获取图像尺寸
        height, width = image_data.shape
        
        # 创建QImage并显示
        qimage = QImage(image_data_uint8.data, width, height, width, QImage.Format_Grayscale8)
        pixmap = QPixmap.fromImage(qimage)
        self.setPixmap(pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))


class EpicsImageMonitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.pv1_name = PV1_NAME
        self.pv2_name = PV2_NAME
        self.image1_data = None
        self.image2_data = None
        
        self.init_ui()
        self.setup_epics_monitors()
        
        # 设置定时器用于定期更新图像显示
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_displays)
        self.update_timer.start(10)  # 每10毫秒更新一次显示
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle('EPICS 图像实时监控系统')
        self.setGeometry(100, 100, 1200, 900)  # 调整窗口高度
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 上半部分：图像显示区域
        upper_layout = QHBoxLayout()
        
        # 创建两个图像显示组
        group1 = QGroupBox(f"PV: {self.pv1_name}")
        layout1 = QVBoxLayout()
        self.image_display1 = ImageDisplayWidget()
        self.pv1_status_label = QLabel(PV1_NAME + "【状态: 未连接】")
        self.pv1_status_label.setStyleSheet("color: red;")
        layout1.addWidget(self.image_display1)
        layout1.addWidget(self.pv1_status_label)  # 状态标签放在图像下方
        group1.setLayout(layout1)
        
        group2 = QGroupBox(f"PV: {self.pv2_name}")
        layout2 = QVBoxLayout()
        self.image_display2 = ImageDisplayWidget()
        self.pv2_status_label = QLabel(PV2_NAME + "【状态: 未连接】")
        self.pv2_status_label.setStyleSheet("color: red;")
        layout2.addWidget(self.image_display2)
        layout2.addWidget(self.pv2_status_label)  # 状态标签放在图像下方
        group2.setLayout(layout2)
        
        # 将两个组添加到上半部分布局
        upper_layout.addWidget(group1)
        upper_layout.addWidget(group2)
        
        # 下半部分：表格区域
        lower_layout = QVBoxLayout()
        self.config_table = QTableWidget()
        self.config_table.setColumnCount(2)  # 两列：配置名和配置内容
        self.config_table.setHorizontalHeaderLabels(["配置名", "配置内容"])
        self.config_table.setStyleSheet("font-size: 14px;")  # 设置表格字体大小
        
        # 设置表格的大小策略为扩展
        self.config_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        lower_layout.addWidget(self.config_table)
        
        # 将上下部分添加到主布局
        main_layout.addLayout(upper_layout, stretch=4)  # 上半部分占4份空间
        main_layout.addLayout(lower_layout, stretch=2)  # 下半部分占2份空间

    def adjust_table_columns(self):
        """调整表格列宽，使每列宽度为窗口宽度的一半"""
        table_width = self.config_table.viewport().width()
        self.config_table.setColumnWidth(0, table_width // 2)  # 第一列宽度
        self.config_table.setColumnWidth(1, table_width // 2)  # 第二列宽度

    def resizeEvent(self, event):
        """在窗口大小调整时动态调整表格列宽"""
        super().resizeEvent(event)
        self.adjust_table_columns()

    def showEvent(self, event):
        """在窗口显示后调整表格列宽"""
        super().showEvent(event)
        self.adjust_table_columns()  # 确保窗口显示后调整列宽

    def setup_epics_monitors(self):
        """设置EPICS监控"""
        self.pv1 = epics.PV(self.pv1_name, form='native', auto_monitor=True)
        self.pv2 = epics.PV(self.pv2_name, form='native', auto_monitor=True)

        # 绑定回调函数
        self.pv1.add_callback(self.on_pv1_update)
        self.pv2.add_callback(self.on_pv2_update)

        # 检查初始连接状态
        self.update_pv1_status(self.pv1.connected)
        self.update_pv2_status(self.pv2.connected)

    def on_pv1_update(self, pvname=None, value=None, **kwargs):
        """PV1更新回调函数"""
        connected = kwargs.get('conn', self.pv1.connected)
        self.update_pv1_status(connected)
        if not connected:
            return
        
        try:
            if value is not None and len(value) == IMAGE_WIDTH * IMAGE_HEIGHT:
                self.image1_data = np.array(value).reshape((IMAGE_HEIGHT, IMAGE_WIDTH))
                QTimer.singleShot(0, self.update_displays)  # 切换到主线程更新界面
            else:
                print(f"PV1数据长度不匹配: 期望 {IMAGE_WIDTH * IMAGE_HEIGHT}, 实际 {len(value) if value is not None else 0}")
        except Exception as e:
            print(f"处理PV1数据时出错: {e}")

    def on_pv2_update(self, pvname=None, value=None, **kwargs):
        """PV2更新回调函数"""
        connected = kwargs.get('conn', self.pv2.connected)
        self.update_pv2_status(connected)
        if not connected:
            return
        
        try:
            if value is not None and len(value) == IMAGE_WIDTH * IMAGE_HEIGHT:
                self.image2_data = np.array(value).reshape((IMAGE_HEIGHT, IMAGE_WIDTH))
                QTimer.singleShot(0, self.update_displays)  # 切换到主线程更新界面
            else:
                print(f"PV2数据长度不匹配: 期望 {IMAGE_WIDTH * IMAGE_HEIGHT}, 实际 {len(value) if value is not None else 0}")
        except Exception as e:
            print(f"处理PV2数据时出错: {e}")

    def update_pv1_status(self, connected):
        """更新PV1的连接状态"""
        if connected:
            self.pv1_status_label.setText(PV1_NAME + "【状态: 已连接】")
            self.pv1_status_label.setStyleSheet("color: green;")
        else:
            self.pv1_status_label.setText(PV1_NAME + "【状态: 未连接】")
            self.pv1_status_label.setStyleSheet("color: red;")
            self.image_display1.clear()  # 清空图像显示
            self.image_display1.setText("PV1 未连接")

    def update_pv2_status(self, connected):
        """更新PV2的连接状态"""
        if connected:
            self.pv2_status_label.setText(PV2_NAME + "【状态: 已连接】")
            self.pv2_status_label.setStyleSheet("color: green;")
        else:
            self.pv2_status_label.setText(PV2_NAME + "【状态: 未连接】")
            self.pv2_status_label.setStyleSheet("color: red;")
            self.image_display2.clear()  # 清空图像显示
            self.image_display2.setText("PV2 未连接")

    def update_displays(self):
        """更新图像显示"""
        if self.image1_data is not None and self.pv1.connected:
            self.image_display1.set_image(self.image1_data)
        else:
            self.image_display1.setText("等待 PV1 图像数据...")
            self.pv1_status_label.setText(PV1_NAME + "【状态: 未连接】")
            self.pv1_status_label.setStyleSheet("color: red;")

        if self.image2_data is not None and self.pv2.connected:
            self.image_display2.set_image(self.image2_data)
        else:
            self.image_display2.setText("等待 PV2 图像数据...")
            self.pv2_status_label.setText(PV2_NAME + "【状态: 未连接】")
            self.pv2_status_label.setStyleSheet("color: red;")
    
    def update_custom_text(self, text):
        """更新自定义文本内容"""
        self.custom_text_label.setText(text)

    def update_config_table(self, config_data):
        """更新表格内容"""
        self.config_table.setRowCount(len(config_data))  # 设置行数
        for row, (key, value) in enumerate(config_data.items()):
            self.config_table.setItem(row, 0, QTableWidgetItem(key))  # 第一列：配置名
            self.config_table.setItem(row, 1, QTableWidgetItem(value))  # 第二列：配置内容
    
    def closeEvent(self, event):
        """应用程序关闭时清理资源"""
        self.update_timer.stop()
        if hasattr(self, 'pv1'):
            self.pv1.clear_auto_monitor()
        if hasattr(self, 'pv2'):
            self.pv2.clear_auto_monitor()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    monitor = EpicsImageMonitor()

    # 添加模型配置信息
    config_data = {
        "模型运行设备": "GPU:0 (CUDA)",
        "模型训练框架": "YOLO11",
        "模型路径": "./src/model/best.pt",
        "图像输入尺寸": "1440 X 1080",
        "清除目标类别": "edges (0), background (1)",
        "保留目标类别": "lights (2)"
    }
     # 更新表格内容
    monitor.update_config_table(config_data)

    monitor.show()
    sys.exit(app.exec_())