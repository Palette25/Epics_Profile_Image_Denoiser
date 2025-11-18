# 软件运行界面
import os
import sys
import yaml
import epics
import logging
import numpy as np

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QGroupBox, QStackedWidget, QPushButton, QGridLayout, QFrame, QToolTip
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap, QPainter, QFont

# 读取全局配置参数
config_path = '../config/config.yaml'
with open(config_path, 'r', encoding='utf-8') as config_file:
    config = yaml.safe_load(config_file)

IMAGE_WIDTH = config['PV_CONFIG']['IMAGE_WIDTH']
IMAGE_HEIGHT = config['PV_CONFIG']['IMAGE_HEIGHT']

fh = logging.FileHandler(config['LOGGING_CONFIG']['VIS_LOG_FILE'], encoding='utf-8')
fh.setLevel(logging.INFO)
fmt = logging.Formatter('%(asctime)s %(message)s')
fh.setFormatter(fmt)
root = logging.getLogger()
root.setLevel(logging.INFO)
root.addHandler(fh)

pv_names_dict = {
    'INJ': {
        'names': ['PRF01', 'PRFB1', 'PRF02', 'PRFB2'],
        'raw': config['PV_CONFIG']['INJ_PROFILE_IMAGE_PVS'],
        'seg': config['PV_CONFIG']['INJ_PROFILE_SEG_IMAGE_PVS']
    },
    'COL': {
        'names': ['PRF01', 'PRF02', 'PRF03', 'PRF04', 'PRF05'],
        'raw': config['PV_CONFIG']['COL_PROFILE_IMAGE_PVS'],
        'seg': config['PV_CONFIG']['COL_PROFILE_SEG_IMAGE_PVS']
    },
    'DIAG0': {
        'names': ['PRF01', 'PRF02', 'PRF03', 'PRF04', 'PRF05', 'PRF06', 'PRF07', 'PRF08', 'PRFB1'],
        'raw': config['PV_CONFIG']['DIAG0_PROFILE_IMAGE_PVS'],
        'seg': config['PV_CONFIG']['DIAG0_PROFILE_SEG_IMAGE_PVS']
    },
    'DIAG1': {
        'names': ['PRF01', 'PRF02', 'PRF03', 'PRF04', 'PRF05', 'PRF06', 'PRF07', 'PRFB1'],
        'raw': config['PV_CONFIG']['DIAG1_PROFILE_IMAGE_PVS'],
        'seg': config['PV_CONFIG']['DIAG1_PROFILE_SEG_IMAGE_PVS']
    }
}

class ImageDisplayWidget(QLabel):
    """用于显示图像的QLabel子类"""
    def __init__(self, pv_name=None, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(800, 600)
        self._pixmap = None
        self.image_shape = (IMAGE_HEIGHT, IMAGE_WIDTH)
        self.axis_left = 50
        self.axis_bottom = 40
        # 记录当前图像所对应的PV名称
        self.pv_name = pv_name
    
    # 定义鼠标中键点击图像时，显示PV名弹窗并复制到剪贴板
    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            # 显示黄色浮窗
            QToolTip.setFont(QFont("DejaVu Sans Mono", 8))
            self.setToolTip(self.pv_name)
            QToolTip.showText(event.globalPos(), self.pv_name, self, self.rect(), 2000)
            # 复制到剪贴板
            clipboard = QApplication.instance().clipboard()
            clipboard.setText(self.pv_name)
        else:
            super().mousePressEvent(event)
    
    # 设置图像内容
    def set_image(self, image_data):
        """将numpy数组转换为QImage并显示"""
        if image_data is None or image_data.size == 0 or len(image_data.shape) != 2:
            self.show_black_image()
            return
            
        # 确保图像数据是二维的
        if len(image_data.shape) != 2:
            self.setText("Invalid Image Data Size!")
            return
            
        # 归一化图像数据到0-255范围
        image_data_uint8 = image_data.astype(np.uint8)
        
        # 获取图像尺寸
        height, width = image_data.shape
        
        # 创建QImage并显示
        self.image_shape = (height, width)
        qimage = QImage(image_data_uint8.data, width, height, width, QImage.Format_Grayscale8)
        self._pixmap = QPixmap.fromImage(qimage)
        self.update()

    def show_black_image(self):
        height, width = self.image_shape
        black = np.zeros((height, width), dtype=np.uint8)
        qimage = QImage(black.data, width, height, width, QImage.Format_Grayscale8)
        self._pixmap = QPixmap.fromImage(qimage)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # 预留坐标轴空间
        axis_left = self.axis_left
        axis_bottom = self.axis_bottom
        area_w = self.width() - axis_left - 10
        area_h = self.height() - axis_bottom - 10

        # 绘制图像
        if self._pixmap:
            img_h, img_w = self.image_shape
            scaled_pixmap = self._pixmap.scaled(area_w, area_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            img_x = axis_left
            img_y = 10
            painter.drawPixmap(img_x, img_y, scaled_pixmap)

            # 计算缩放比例
            scale_w = scaled_pixmap.width() / img_w
            scale_h = scaled_pixmap.height() / img_h

            # 绘制坐标轴
            axis_x0 = axis_left
            axis_y0 = img_y + scaled_pixmap.height()
            axis_x1 = axis_left + scaled_pixmap.width()
            axis_y1 = axis_y0

            # 横轴
            painter.setPen(Qt.black)
            painter.drawLine(axis_x0, axis_y0, axis_x1, axis_y1)
            for x in range(0, img_w+1, 100):
                px = axis_x0 + int(x * scale_w)
                painter.drawLine(px, axis_y0, px, axis_y0 + 8)
                painter.drawText(px-12, axis_y0 + 25, f"{x}")

            # 纵轴
            axis_y_top = img_y
            painter.drawLine(axis_x0, axis_y0, axis_x0, axis_y_top)
            for y in range(0, img_h+1, 100):
                py = axis_y0 - int(y * scale_h)
                painter.drawLine(axis_x0-8, py, axis_x0, py)
                painter.drawText(axis_x0-45, py+5, f"{y}")

        else:
            # 没有图像时显示全黑
            painter.fillRect(axis_left, 10, self.width()-axis_left-10, self.height()-axis_bottom-10, Qt.black)
            # 坐标轴也要画
            img_w, img_h = self.image_shape
            scale_w = (self.width()-axis_left-10) / img_w
            scale_h = (self.height()-axis_bottom-10) / img_h
            axis_x0 = axis_left
            axis_y0 = self.height() - axis_bottom
            axis_x1 = self.width() - 10
            axis_y1 = axis_y0
            painter.setPen(Qt.white)
            painter.drawLine(axis_x0, axis_y0, axis_x1, axis_y1)
            for x in range(0, img_w+1, 100):
                px = axis_x0 + int(x * scale_w)
                painter.drawLine(px, axis_y0, px, axis_y0 + 8)
                painter.drawText(px-12, axis_y0 + 25, f"{x}")
            axis_y_top = 10
            painter.drawLine(axis_x0, axis_y0, axis_x0, axis_y_top)
            for y in range(0, img_h+1, 100):
                py = axis_y0 - int(y * scale_h)
                painter.drawLine(axis_x0-8, py, axis_x0, py)
                painter.drawText(axis_x0-45, py+5, f"{y}")

class ProfileImagePage(QWidget):
    def __init__(self, PV1_NAME, PV2_NAME):
        super().__init__()
        self.pv1_name = PV1_NAME
        self.pv2_name = PV2_NAME
        self.image1_data = None
        self.image2_data = None

        self.init_ui()
        self.setup_epics_monitors()

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_displays)
        self.update_timer.start(10)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        upper_layout = QHBoxLayout()
        upper_layout.setAlignment(Qt.AlignCenter)  # 让内容居中
        # 左侧图像显示区域
        group1 = QGroupBox(f"Raw CCD IMAGE")
        layout1 = QVBoxLayout()
        self.image_display1 = ImageDisplayWidget(pv_name=self.pv1_name)
        self.pv1_status_label = QLabel(self.pv1_name + "【State: Not Connected】")
        self.pv1_status_label.setStyleSheet("color: red;")
        layout1.addWidget(self.image_display1)
        layout1.addWidget(self.pv1_status_label)
        group1.setLayout(layout1)
        # 右侧图像显示区域
        group2 = QGroupBox(f"Processed CCD IMAGE")
        layout2 = QVBoxLayout()
        self.image_display2 = ImageDisplayWidget(pv_name=self.pv2_name)
        self.pv2_status_label = QLabel(self.pv2_name + "【State: Not Connected】")
        self.pv2_status_label.setStyleSheet("color: red;")
        layout2.addWidget(self.image_display2)
        layout2.addWidget(self.pv2_status_label)
        group2.setLayout(layout2)
        # 布局组合
        upper_layout.addWidget(group1)
        upper_layout.addWidget(group2)
        main_layout.addLayout(upper_layout, stretch=4)

        # ====== 新增：参数文本区域 ======
        self.config_text_widget = QWidget()
        self.config_text_layout = QGridLayout(self.config_text_widget)
        self.config_text_layout.setContentsMargins(10, 10, 10, 10)
        self.config_text_layout.setSpacing(0)

        # 第一行：居中标题
        self.title_label = QLabel("Profile Image Segmentation Model Configuration Parameters")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet(
            "background-color:#003366; color:white; font-size:20px; font-weight:bold; border-radius:8px; padding:8px 0;"
        )
        self.config_text_layout.addWidget(self.title_label, 0, 0, 1, 7)  # 跨7列

        # 第二行：参数标签和分隔线
        self.param_labels = []
        for col in range(4):
            label = QLabel()
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet(
                "background-color:#d3d3d3; color:black; font-size:15px; font-weight:bold; border:none; padding:8px 0;"
            )
            self.config_text_layout.addWidget(label, 1, col*2)
            self.param_labels.append(label)
            if col < 3:
                line = QFrame()
                line.setFrameShape(QFrame.VLine)
                line.setFrameShadow(QFrame.Sunken)
                line.setStyleSheet("background-color:#bbbbbb; min-width:2px; max-width:2px;")
                self.config_text_layout.addWidget(line, 1, col*2+1)

        # 在第二行和第三行之间插入一条横线
        hline = QFrame()
        hline.setFrameShape(QFrame.HLine)
        hline.setFrameShadow(QFrame.Sunken)
        hline.setStyleSheet("background-color:#bbbbbb; min-height:2px; max-height:2px;")
        self.config_text_layout.addWidget(hline, 2, 0, 1, 7)  # 跨7列

        # 第三行：参数标签和分隔线
        for col in range(4):
            label = QLabel()
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet(
                "background-color:#d3d3d3; color:black; font-size:15px; font-weight:bold; border:none; padding:8px 0;"
            )
            self.config_text_layout.addWidget(label, 3, col*2)
            self.param_labels.append(label)
            if col < 3:
                line = QFrame()
                line.setFrameShape(QFrame.VLine)
                line.setFrameShadow(QFrame.Sunken)
                line.setStyleSheet("background-color:#bbbbbb; min-width:2px; max-width:2px;")
                self.config_text_layout.addWidget(line, 3, col*2+1)

        main_layout.addWidget(self.config_text_widget, stretch=1)

    def setup_epics_monitors(self):
        self.pv1 = epics.PV(self.pv1_name, form='native', auto_monitor=True, connection_callback=self.update_pv1_status)
        self.pv2 = epics.PV(self.pv2_name, form='native', auto_monitor=True, connection_callback=self.update_pv2_status)
        self.pv1.add_callback(self.on_pv1_update)
        self.pv2.add_callback(self.on_pv2_update)

    def on_pv1_update(self, pvname=None, value=None, **kwargs):
        # 更新连接状态
        connected = kwargs.get('conn', self.pv1.connected)
        self.update_pv1_status(pvname, connected, **kwargs)
        if not connected:
            return
        try:
            if value is not None and len(value) == IMAGE_WIDTH * IMAGE_HEIGHT:
                self.image1_data = np.array(value).reshape((IMAGE_HEIGHT, IMAGE_WIDTH))
                QTimer.singleShot(0, self.update_displays)
            else:
                logging.error(f"PV1数据长度不匹配: 期望 {IMAGE_WIDTH * IMAGE_HEIGHT}, 实际 {len(value) if value is not None else 0}")
        except Exception as e:
            logging.error(f"处理PV1数据时出错: {e}")

    def on_pv2_update(self, pvname=None, value=None, **kwargs):
        # 更新连接状态
        connected = kwargs.get('conn', self.pv2.connected)
        self.update_pv2_status(pvname, connected, **kwargs)
        if not connected:
            return
        try:
            if value is not None and len(value) == IMAGE_WIDTH * IMAGE_HEIGHT:
                self.image2_data = np.array(value).reshape((IMAGE_HEIGHT, IMAGE_WIDTH))
                QTimer.singleShot(0, self.update_displays)
            else:
                logging.error(f"PV2数据长度不匹配: 期望 {IMAGE_WIDTH * IMAGE_HEIGHT}, 实际 {len(value) if value is not None else 0}")
        except Exception as e:
            logging.error(f"处理PV2数据时出错: {e}")
    
    # PV连接状态更新
    def update_pv1_status(self, pvname=None, conn=None, **kws):
        if conn:
            self.pv1_status_label.setText(self.pv1_name + "【State: Connected】")
            self.pv1_status_label.setStyleSheet("color: green;")
        else:
            self.pv1_status_label.setText(self.pv1_name + "【State: Not Connected】")
            self.pv1_status_label.setStyleSheet("color: red;")

    def update_pv2_status(self, pvname=None, conn=None, **kws):
        if conn:
            self.pv2_status_label.setText(self.pv2_name + "【State: Connected】")
            self.pv2_status_label.setStyleSheet("color: green;")
        else:
            self.pv2_status_label.setText(self.pv2_name + "【State: Not Connected】")
            self.pv2_status_label.setStyleSheet("color: red;")

    # 实时更新图像内容，以及对应的连接状态栏显示
    def update_displays(self):
        # 仅当有新数据且PV连接时更新PV1图像
        if self.image1_data is not None and self.pv1.connected:
            self.image_display1.set_image(self.image1_data)
        else:
            self.image_display1.show_black_image()
            if not self.pv1.connected:
                self.pv1_status_label.setText(self.pv1_name + "【State: Not Connected】")
                self.pv1_status_label.setStyleSheet("color: red;")

        if self.image2_data is not None and self.pv2.connected:
            self.image_display2.set_image(self.image2_data)
        else:
            self.image_display2.show_black_image()
            if not self.pv2.connected:
                self.pv2_status_label.setText(self.pv1_name + "【State: Not Connected】")
                self.pv2_status_label.setStyleSheet("color: red;")

    def update_config_table(self, config_data):
        # config_data: dict
        # 展示到第二、三行，每行4个，key:value格式
        items = [f"{k}: {v}" for k, v in config_data.items()]
        for i in range(8):
            if i < len(items):
                self.param_labels[i].setText(items[i])
            else:
                self.param_labels[i].setText("")

    def closeEvent(self, event):
        self.update_timer.stop()
        if hasattr(self, 'pv1'):
            self.pv1.clear_auto_monitor()
        if hasattr(self, 'pv2'):
            self.pv2.clear_auto_monitor()
        event.accept()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # 设置全局字体
        font = QFont("DejaVu Sans Mono", 9)
        font.setStyleStrategy(QFont.PreferAntialias)
        QApplication.instance().setFont(font)

        self.setWindowTitle('EPICS Image Real-time Monitoring System')
        self.setGeometry(100, 100, 1200, 900)

        self.stacked_widget = QStackedWidget()
        self.pages = {}
        self.page_indices = {}

        # 页面实例化
        for section, info in pv_names_dict.items():
            for idx, name in enumerate(info['names']):
                raw_pv = info['raw'][idx]
                seg_pv = info['seg'][idx]
                page = ProfileImagePage(raw_pv, seg_pv)
                self.pages[(section, idx)] = page
                index = self.stacked_widget.addWidget(page)
                self.page_indices[(section, idx)] = index

        # 一级菜单
        self.section_names = list(pv_names_dict.keys())
        self.current_section = self.section_names[0]
        self.current_sub_idx = 0

        self.section_layout = QHBoxLayout()
        self.section_buttons = []
        for section in self.section_names:
            btn = QPushButton(section)
            btn.setFixedHeight(32)
            btn.setStyleSheet("margin:2px; padding:4px 12px;")
            btn.clicked.connect(lambda checked, s=section: self.switch_section(s))
            self.section_layout.addWidget(btn)
            self.section_buttons.append(btn)

        # 二级菜单
        self.subsection_layout = QHBoxLayout()
        self.subsection_buttons = []
        self.update_subsection_buttons(self.current_section)

        # 菜单区容器
        menu_widget = QWidget()
        menu_layout = QVBoxLayout(menu_widget)
        menu_layout.setSpacing(2)
        menu_layout.setContentsMargins(2,2,2,2)
        menu_layout.addLayout(self.section_layout)
        menu_layout.addLayout(self.subsection_layout)

        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(2)
        main_layout.setContentsMargins(2,2,2,2)
        main_layout.addWidget(menu_widget)
        main_layout.addWidget(self.stacked_widget)
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        self.stacked_widget.setCurrentIndex(self.page_indices[(self.current_section, 0)])
        self.update_section_highlight()
        self.update_subsection_highlight()

        config_data = {
            "Model Running Device": "GPU:0 (CUDA)",
            "Model Training Strcuture": "YOLO11",
            "Model Loading Path": "./src/model/best.pt",
            "Input Image Size": "1280 X 1024",
            "Clean Target Classes": "edges(0), background(1)",
            "Keep Target Classes": "lights(2)",
            "Confidence Threshold": "0.25",
            "NMS IoU Threshold": "0.45",
        }
        for page in self.pages.values():
            page.update_config_table(config_data)

    def update_subsection_buttons(self, section):
        for btn in self.subsection_buttons:
            self.subsection_layout.removeWidget(btn)
            btn.deleteLater()
        self.subsection_buttons = []
        for idx, name in enumerate(pv_names_dict[section]['names']):
            btn = QPushButton(name)
            btn.setFixedHeight(28)
            btn.setStyleSheet("margin:2px; padding:2px 8px;")
            btn.clicked.connect(lambda checked, i=idx: self.switch_page(section, i))
            self.subsection_layout.addWidget(btn)
            self.subsection_buttons.append(btn)

    def switch_section(self, section):
        self.current_section = section
        self.current_sub_idx = 0
        self.update_subsection_buttons(section)
        self.switch_page(section, 0)
        self.update_section_highlight()
        self.update_subsection_highlight()

    def switch_page(self, section, idx):
        self.current_section = section
        self.current_sub_idx = idx
        index = self.page_indices[(section, idx)]
        self.stacked_widget.setCurrentIndex(index)
        self.update_section_highlight()
        self.update_subsection_highlight()

    def update_section_highlight(self):
        for i, btn in enumerate(self.section_buttons):
            if self.section_names[i] == self.current_section:
                btn.setStyleSheet("background-color:#0078d7; color:white; font-weight:bold; margin:2px; padding:4px 12px; border-radius:6px;")
            else:
                btn.setStyleSheet("background-color:#eaeaea; color:#333; margin:2px; padding:4px 12px; border-radius:6px;")

    def update_subsection_highlight(self):
        for i, btn in enumerate(self.subsection_buttons):
            if i == self.current_sub_idx:
                btn.setStyleSheet("background-color:#0078d7; color:white; font-weight:bold; margin:2px; padding:2px 8px; border-radius:6px;")
            else:
                btn.setStyleSheet("background-color:#eaeaea; color:#333; margin:2px; padding:2px 8px; border-radius:6px;")

    def closeEvent(self, event):
        for page in self.pages.values():
            page.closeEvent(event)
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())