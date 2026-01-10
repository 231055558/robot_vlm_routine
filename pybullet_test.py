import pybullet as p
import pybullet_data
import time

# --- 1. 连接仿真环境 ---
# p.GUI 会弹出一个可视化的窗口
physicsClient = p.connect(p.GUI)

# 设置额外的资源路径，确保能加载到默认的地面模型
p.setAdditionalSearchPath(pybullet_data.getDataPath())

# 设置重力 (地球重力，向下 9.8)
p.setGravity(0, 0, -9.8)

# --- 2. 加载场景 ---
# 加载地面
planeId = p.loadURDF("plane.urdf")

# --- 3. 搭建简单的“快递站” (程序化生成，不需要下载模型) ---

# A. 创建一个桌子/分拣台 (用一个大的蓝色方块代替)
table_visual = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.5, 1, 0.3], rgbaColor=[0.2, 0.2, 0.2, 1]) # 深灰色
table_col = p.createCollisionShape(p.GEOM_BOX, halfExtents=[0.5, 1, 0.3])
# basePosition是中心点坐标，所以Z=0.3意味着桌面高度是0.6
tableId = p.createMultiBody(baseMass=0, baseCollisionShapeIndex=table_col, baseVisualShapeIndex=table_visual, basePosition=[0, 0, 0.3])

# B. 生成几个快递包裹 (不同颜色的方块)
# 定义包裹：[颜色RGB, 初始位置XYZ]
packages = [
    ([1, 0, 0, 1], [0, 0.2, 1.0]),   # 红色包裹，在桌子上空
    ([0, 1, 0, 1], [0, -0.2, 1.2]),  # 绿色包裹，更高一点
    ([0, 0, 1, 1], [0.2, 0, 1.5])    # 蓝色包裹
]

for color, pos in packages:
    # 尺寸：10cm * 10cm * 10cm 的盒子
    box_visual = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.05, 0.05, 0.05], rgbaColor=color)
    box_col = p.createCollisionShape(p.GEOM_BOX, halfExtents=[0.05, 0.05, 0.05])
    # baseMass=1 表示它重1kg，会受重力影响
    p.createMultiBody(baseMass=1, baseCollisionShapeIndex=box_col, baseVisualShapeIndex=box_visual, basePosition=pos)

# --- 4. 运行仿真 ---
print("仿真环境已启动！按 Ctrl+C 退出。")
while True:
    p.stepSimulation()
    time.sleep(1./240.) # 模拟真实的物理时间步长