#!/usr/bin/env python3
"""
将 TEST:IMAGE PV 设置为全 1 的 uint8 数组 (1440x1080)
支持本地和跨主机连接，已针对 EPICS 7.0.4 优化
"""
import os
import time
import numpy as np
from epics import PV, ca

# ======================
# 配置区域 (根据您的环境修改)
# ======================
SERVER_IP = "127.0.0.1"  # 服务器IP，本地连接用 "127.0.0.1"
PV_NAME = "INJ-BI:PRF01:CCD_SEG_IMAGE"
ARRAY_SIZE = 1440 * 1080  # 1,555,200 个元素
TIMEOUT = 10.0  # 连接超时时间(秒)
# ======================

def setup_epics_client(server_ip):
    """配置EPICS客户端环境（必须在导入epics前设置）"""
    os.environ.update({
        "EPICS_CA_ADDR_LIST": server_ip,
        "EPICS_CA_AUTO_ADDR_LIST": "NO",
        "EPICS_CA_MAX_ARRAY_BYTES": str(ARRAY_SIZE * 2),  # 2倍安全余量
        "EPICS_CA_AUTO_VERSION": "6",  # EPICS 7 关键
        "EPICS_CA_CONN_TMO": "5.0",    # 连接超时
        "EPICS_CA_REPEATER_PORT": "5065"  # UDP广播端口
    })
    ca.initialize_libca()  # 重新初始化CA库

def create_full_one_array(size):
    """创建全1的uint8数组（高效内存方案）"""
    
    # 方案2：内存优化 (适用于超大数组)
    return np.full(size, 50, dtype=np.uint8)
    
    # 方案3：避免大内存分配 (分块写入)
    # return (1).to_bytes(1, 'little') * size  # 仅适用于raw模式

def set_pv_to_full_one(pv_name, array_size, timeout=5.0):
    """将PV设置为全1数组的核心函数"""
    # 1. 创建PV对象
    pv = PV(pv_name, connection_timeout=timeout, form='native')
    
    # 2. 等待连接建立
    print(f"Connecting to {pv_name}...", end="", flush=True)
    start_time = time.time()
    while not pv.connected:
        if time.time() - start_time > timeout:
            raise ConnectionError(f"Failed to connect to {pv_name} within {timeout}s")
        print(".", end="", flush=True)
        time.sleep(0.5)
    print("\nConnected successfully!")
    
    # 3. 创建全1数组 (高效方案)
    print(f"Creating {array_size:,} element uint8 array filled with 1s...")
    start_create = time.time()
    data = create_full_one_array(array_size)
    create_time = time.time() - start_create
    print(f"Array created in {create_time:.3f}s | Memory: {data.nbytes/1024:.1f} KB")
    
    # 4. 写入PV (关键：使用put完成)
    print("Writing to PV...", end="", flush=True)
    start_write = time.time()
    
    # 方案A：直接put (推荐，最快)
    pv.put(data, wait=True, timeout=timeout)

    
    write_time = time.time() - start_write
    print(f" Done! ({write_time:.3f}s)")

def main():
    """主执行流程"""
    try:
        # 1. 设置客户端环境
        setup_epics_client(SERVER_IP)
        
        # 2. 执行核心操作
        success = set_pv_to_full_one(PV_NAME, ARRAY_SIZE, TIMEOUT)
        
    
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {str(e)}")
        print("Troubleshooting tips:")
        print("1. Check if softIoc is running: ps aux | grep softIoc")
        print("2. Verify network: ping", SERVER_IP)
        print("3. Check firewall: sudo ufw status (should allow 5064-5065/udp)")
        raise

if __name__ == "__main__":
    main()