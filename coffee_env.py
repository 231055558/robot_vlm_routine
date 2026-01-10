import pybullet as p
import pybullet_data
import time
import math
import threading # 引入多线程库

class CoffeeShopServer:
    def __init__(self):
        # p.GUI_SERVER: 启动图形界面
        self.connection_mode = p.GUI_SERVER 
        p.connect(self.connection_mode)
        
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, 0, -9.8)
        # 调整上帝视角
        p.resetDebugVisualizerCamera(cameraDistance=1.8, cameraYaw=0, cameraPitch=-40, cameraTargetPosition=[0, -0.2, 0.6])
        p.loadURDF("plane.urdf")

        self.robotId = None
        # --- 新增：用于存储瓶子信息的列表 ---
        # 结构: [{"id": uid, "init_pos": [x,y,z]}, ...]
        self.bottle_records = []
        
        self._create_scene()
        self._create_camera()

        # --- 新增：启动键盘监听线程 ---
        self.running = True
        self.input_thread = threading.Thread(target=self._console_input_loop)
        self.input_thread.daemon = True # 设置为守护线程，主程序退出时它也会退出
        self.input_thread.start()

    def _create_scene(self):
        # 2.创建吧台和货架
        table_h = 0.7
        p.createMultiBody(baseMass=0, baseCollisionShapeIndex=p.createCollisionShape(p.GEOM_BOX, halfExtents=[0.8, 0.5, 0.05]), baseVisualShapeIndex=p.createVisualShape(p.GEOM_BOX, halfExtents=[0.8, 0.5, 0.05], rgbaColor=[0.25, 0.15, 0.1, 1]), basePosition=[0, 0, table_h])
        
        shelf_start_y = 0.1; shelf_step_height = 0.15; shelf_step_depth = 0
        for i in range(3):
            h = table_h + 0.05 + (i * shelf_step_height); y = shelf_start_y + (i * shelf_step_depth)
            p.createMultiBody(baseMass=0, baseVisualShapeIndex=p.createVisualShape(p.GEOM_BOX, halfExtents=[0.3, 0.06, 0.01], rgbaColor=[0.15, 0.15, 0.15, 1]), baseCollisionShapeIndex=p.createCollisionShape(p.GEOM_BOX, halfExtents=[0.3, 0.06, 0.01]), basePosition=[0, y, h])
        
        # 3.创建原料
        ingredients_data = [
            # Row 0 (1-3)
            {"description":"浓缩咖啡", "text": "ESPRESSO", "body": [0.1, 0.05, 0.0, 1],    "font": [1, 1, 1], "row": 0, "col": 0},
            {"description":"水",      "text": "WATER",    "body": [0.0, 0.4, 0.8, 1],  "font": [1, 1, 1], "row": 0, "col": 1},
            {"description":"牛奶",    "text": "MILK",     "body": [1.0, 1.0, 1.0, 1],    "font": [0, 0, 0], "row": 0, "col": 2},
            # Row 1 (4-6)
            {"description":"香草",    "text": "VANILLA",  "body": [1.0, 0.9, 0.2, 1],    "font": [0, 0, 0], "row": 1, "col": 0},
            {"description":"焦糖",    "text": "CARAMEL",  "body": [1.0, 0.5, 0.0, 1],    "font": [0, 0, 0], "row": 1, "col": 1},
            {"description":"可可",    "text": "CHOCO",    "body": [0.6, 0.3, 0.1, 1],    "font": [1, 1, 1], "row": 1, "col": 2},
            # Row 2 (7-9)
            {"description":"燕麦奶",  "text": "OAT",      "body": [0.8, 0.7, 0.5, 1],    "font": [0, 0, 0], "row": 2, "col": 0},
            {"description":"糖",      "text": "SUGAR",    "body": [0.7, 0.7, 0.7, 1],    "font": [0, 0, 0], "row": 2, "col": 1},
            {"description":"冰",      "text": "ICE",      "body": [0.5, 0.9, 1.0, 1],  "font": [0, 0, 0], "row": 2, "col": 2}
        ]
        bottle_w = 0.025; bottle_h = 0.05
        
        # 清空记录，防止重建场景时重复添加
        self.bottle_records = []

        for item in ingredients_data:
            pos_x = (item["col"] - 1) * 0.2; pos_y = shelf_start_y + (item["row"] * shelf_step_depth); pos_z = table_h + 0.09 + (item["row"] * shelf_step_height) + bottle_h
            vis_shape = p.createVisualShape(p.GEOM_BOX, halfExtents=[bottle_w, bottle_w, bottle_h], rgbaColor=item["body"])
            col_shape = p.createCollisionShape(p.GEOM_BOX, halfExtents=[bottle_w, bottle_w, bottle_h])
            
            # 创建物体
            uid = p.createMultiBody(baseMass=1.0, baseCollisionShapeIndex=col_shape, baseVisualShapeIndex=vis_shape, basePosition=[pos_x, pos_y, pos_z])
            
            # 添加文字标签
            p.addUserDebugText(text=item["text"], textPosition=[-0.1, -0.136, 0.02], textColorRGB=item["font"], textSize=1.4, parentObjectUniqueId=uid)

            # --- 关键：记录 ID 和 初始位置 ---
            self.bottle_records.append({
                "id": uid,
                "init_pos": [pos_x, pos_y, pos_z],
                "init_orn": [0, 0, 0, 1], # 默认四元数
                "name": item["text"]
            })

        # 4.创建咖啡杯
        p.createMultiBody(baseMass=0.5,
        baseVisualShapeIndex=p.createVisualShape(p.GEOM_CYLINDER, radius=0.05, length=0.12, rgbaColor=[1,1,1,1]),
        baseCollisionShapeIndex=p.createCollisionShape(p.GEOM_CYLINDER, radius=0.05, height=0.12),
        basePosition=[-0.4, -0.2, table_h + 0.08])

        # 5.创建机器人
        robot_start_pos = [-0.3, -0.65, table_h] 
        robot_start_orn = p.getQuaternionFromEuler([0, 0, 0]) 
        self.robotId = p.loadURDF("franka_panda/panda.urdf", robot_start_pos, robot_start_orn, useFixedBase=True)

        # 6.设置机器人初始姿态
        home_joints = [0.0, -0.24, 0.0, -2.0, 0.0, 1.8, 0.8] 
        for i in range(7):
            p.resetJointState(self.robotId, i, home_joints[i])
        p.resetJointState(self.robotId, 9, 0.04)
        p.resetJointState(self.robotId, 10, 0.04)
        
    def _create_camera(self):
        self.camera_pos = [0, -0.5, 1.3] 
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=p.createVisualShape(p.GEOM_BOX, halfExtents=[0.05, 0.02, 0.02], rgbaColor=[0, 1, 0, 1]), basePosition=self.camera_pos)

    # --- 新增功能：重置场景 ---
    def reset_scene(self):
        print(">>> 正在重置场景到初始状态...")
        
        # 1. 重置所有瓶子
        for record in self.bottle_records:
            uid = record["id"]
            init_pos = record["init_pos"]
            p.resetBasePositionAndOrientation(uid, init_pos, [0,0,0,1])
            
        # 2. 重置机械臂 (Franka Panda)
        # 定义初始姿态 (弯曲状态)
        home_joints = [0.0, -0.24, 0.0, -2.0, 0.0, 1.8, 0.8] 
        
        # 重置手臂关节 (0-6)
        for i in range(7):
            p.resetJointState(self.robotId, i, home_joints[i])
            # 重要：同时要把电机的目标位置也重置，否则物理引擎下一帧又会把手臂拉回去
            p.setJointMotorControl2(self.robotId, i, p.POSITION_CONTROL, targetPosition=home_joints[i], force=200)
            
        # 重置夹爪 (9-10) -> 张开
        p.resetJointState(self.robotId, 9, 0.04)
        p.resetJointState(self.robotId, 10, 0.04)
        p.setJointMotorControl2(self.robotId, 9, p.POSITION_CONTROL, targetPosition=0.04, force=200)
        p.setJointMotorControl2(self.robotId, 10, p.POSITION_CONTROL, targetPosition=0.04, force=200)

        print(">>> 重置完成 (瓶子 + 机械臂)！")

    # --- 新增功能：交换瓶子 ---
    def swap_bottles(self, idx1, idx2):
        # 检查索引是否有效 (输入的 1-9 需要转为 0-8)
        if not (0 <= idx1 < len(self.bottle_records)) or not (0 <= idx2 < len(self.bottle_records)):
            print(f"❌ 索引错误：请输入 1-9 之间的数字。")
            return

        print(f">>> 正在交换瓶子 {idx1+1} ({self.bottle_records[idx1]['name']}) 和 {idx2+1} ({self.bottle_records[idx2]['name']})...")
        
        # 获取两个物体的 ID
        id1 = self.bottle_records[idx1]["id"]
        id2 = self.bottle_records[idx2]["id"]

        # 获取它们当前在仿真中的物理位置
        pos1, orn1 = p.getBasePositionAndOrientation(id1)
        pos2, orn2 = p.getBasePositionAndOrientation(id2)

        # 交叉设置位置 (瞬移)
        p.resetBasePositionAndOrientation(id1, pos2, orn1) # 1 去 2 的位置
        p.resetBasePositionAndOrientation(id2, pos1, orn2) # 2 去 1 的位置
        print(">>> 交换完成！")

    # --- 新增功能：键盘监听循环 ---
    def _console_input_loop(self):
        print("\n" + "="*50)
        print("【指令说明】")
        print("输入 '0'  -> 重置场景")
        print("输入 '19' -> 交换第1个和第9个瓶子")
        print("输入 '25' -> 交换第2个和第5个瓶子")
        print("..." + "="*50 + "\n")

        while self.running:
            try:
                # 获取用户输入
                cmd = input()
                
                if cmd == '0':
                    self.reset_scene()
                
                elif len(cmd) == 2 and cmd.isdigit():
                    # 解析两位数字，例如 '19'
                    idx1 = int(cmd[0]) - 1 # 转为列表索引 (0-based)
                    idx2 = int(cmd[1]) - 1
                    
                    # 避免自己换自己
                    if idx1 != idx2:
                        self.swap_bottles(idx1, idx2)
                    else:
                        print("自己换自己？没必要吧。")
                else:
                    print("无效指令。请输入 '0' 或两位数字(如 '19')。")
                    
            except Exception as e:
                print(f"输入处理错误: {e}")

    def run(self):
        try:
            while True:
                p.stepSimulation()
                time.sleep(1./240.)
        except KeyboardInterrupt:
            self.running = False
            print("程序退出。")

if __name__ == "__main__":
    server = CoffeeShopServer()
    server.run()