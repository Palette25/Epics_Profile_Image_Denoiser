import re
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime

# 设置中文显示
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

def parse_debug_logs(log_path):
    pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \[Debug\] (.+耗时): (\d+\.\d+)s'
    data = []
    
    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            if '耗时' in line and '队列' not in line and '整体' not in line and '模型' not in line:
                match = re.search(pattern, line)
                if match:
                    data.append({
                        'timestamp': datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S,%f'),
                        'operation': match.group(2).strip(),
                        'duration': float(match.group(3))
                    })

    return pd.DataFrame(data)[4:124]

def visualize_timeline(df):
    plt.figure(figsize=(18, 9))
    
    operations = df['operation'].unique()
    colors = plt.cm.tab20(range(len(operations)))
    
    for idx, op in enumerate(operations):
        subset = df[df['operation'] == op].sort_values('timestamp')
        plt.plot(subset['timestamp'], subset['duration']*1000,
                 color=colors[idx],
                 linewidth=2,
                 marker='.',
                 label=op)
        
        # 计算并添加平均耗时
        avg_duration = subset['duration'].mean()
        print(f"{op} 平均耗时: {avg_duration*1000:.2f}ms")

    plt.title('Epics图像增强处理-各部分耗时曲线', fontsize=18, pad=25)
    plt.xlabel('时间戳', fontsize=14)
    plt.ylabel('耗时 (毫秒)', fontsize=14)
    plt.xticks(rotation=40, fontsize=12)
    plt.yticks(fontsize=12)
    plt.grid(True, alpha=0.2)
    
    plt.legend()

    output_dir = Path('../logging/performance_graphs')
    output_dir.mkdir(exist_ok=True)
    save_path = output_dir / f'operation_timeline_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"\n图表保存路径：{save_path}")

if __name__ == '__main__':
    try:
        import pandas as pd
        import matplotlib
    except ImportError:
        print("请先安装依赖：pip install pandas matplotlib")
        exit(1)

    df = parse_debug_logs(Path('../logging/service.log'))
    
    if not df.empty:
        print(f"\n找到{len(df)}条耗时记录")
        print("操作类型分布：")
        print(df['operation'].value_counts().to_string())
        
        visualize_timeline(df)
    else:
        print("未找到有效的耗时记录")