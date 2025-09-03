# 工具函数合集
import epics

# 检测框按比例扩展（与按照固定比例截取不同，而是按照检测框真实比例，等比扩展）
def expand_bbox(x_min, y_min, x_max, y_max, img_width, img_height):
    """
    将检测框的长宽按中心点扩展两倍，并处理边界越界情况
    
    参数:
        x_min, y_min, x_max, y_max: 原始检测框坐标（支持浮点数或整数）
        img_width, img_height: 图像尺寸
    
    返回:
        (new_x_min, new_y_min, new_x_max, new_y_max)
    """
    # 计算原始检测框中心点
    cx = (x_min + x_max) / 2
    cy = (y_min + y_max) / 2
    
    # 计算原始宽高
    original_width = x_max - x_min
    original_height = y_max - y_min
    
    # 扩展为两倍
    new_width = original_width * 2
    new_height = original_height * 2
    
    # 计算新坐标
    new_x_min = max(0, cx - new_width / 2)          # 左边界保护
    new_x_max = min(img_width, cx + new_width / 2)  # 右边界保护
    new_y_min = max(0, cy - new_height / 2)         # 上边界保护
    new_y_max = min(img_height, cy + new_height / 2) # 下边界保护
    
    # 返回结果（保持原始数据类型）
    return (
        new_x_min, 
        new_y_min,
        new_x_max,
        new_y_max
    )

# PV操作函数
def monitor_image_pv(pv_name, callback):
    """
    监控 EPICS PV 的变化，并在变化时调用回调函数。
    
    参数:
        pv_name: 要监控的 PV 名称
        callback: 当 PV 值变化时调用的回调函数，接收参数 (pvname, value, **kwargs)
    """
    image_pv = epics.PV(pv_name, form='native', auto_monitor=True)
    
    if not image_pv.wait_for_connection(timeout=5.0): # 等待PV连接，超时5秒
        raise ValueError(f"无法连接到 PV: {pv_name}")
    
    # 添加回调函数
    image_pv.add_callback(callback)

def send_result_to_pv(result_pv_name, result_pv, result_image):
    """将处理后的图像和检测结果发送回 EPICS"""
    # 更新 EPICS PV最新值
    result_pv.put(result_image.flatten(), wait=False)
