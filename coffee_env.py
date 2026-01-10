import pybullet as p
import pybullet_data
import time
import threading

class CoffeeShopServer:
    """PyBullet 仿真环境：咖啡厅场景与机械臂"""

    def __init__(self):
        self.connection_mode = p.GUI_SERVER
        p.connect(self.connection_mode)

        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, 0, -9.8)
        p.resetDebugVisualizerCamera(
            cameraDistance=1.8, cameraYaw=0, cameraPitch=-40,
            cameraTargetPosition=[0, -0.2, 0.6]
        )
        p.loadURDF("plane.urdf")

        self.robotId = None
        self.bottle_records = []  # 存储瓶子信息

        self._create_scene()
        self._create_camera()

        # 启动键盘监听线程
        self.running = True
        self.input_thread = threading.Thread(target=self._console_input_loop)
        self.input_thread.daemon = True
        self.input_thread.start()

    def _create_scene(self):
        """创建吧台、货架、原料瓶、咖啡杯和机械臂"""
        table_h = 0.7

        # 吧台
        p.createMultiBody(
            baseMass=0,
            baseCollisionShapeIndex=p.createCollisionShape(p.GEOM_BOX, halfExtents=[0.8, 0.5, 0.05]),
            baseVisualShapeIndex=p.createVisualShape(p.GEOM_BOX, halfExtents=[0.8, 0.5, 0.05], rgbaColor=[0.25, 0.15, 0.1, 1]),
            basePosition=[0, 0, table_h]
        )

        # 货架 (3 层)
        shelf_start_y = 0.1
        shelf_step_height = 0.15
        for i in range(3):
            h = table_h + 0.05 + (i * shelf_step_height)
            p.createMultiBody(
                baseMass=0,
                baseVisualShapeIndex=p.createVisualShape(p.GEOM_BOX, halfExtents=[0.3, 0.06, 0.01], rgbaColor=[0.15, 0.15, 0.15, 1]),
                baseCollisionShapeIndex=p.createCollisionShape(p.GEOM_BOX, halfExtents=[0.3, 0.06, 0.01]),
                basePosition=[0, shelf_start_y, h]
            )

        # 原料瓶 (3x3 = 9 个)
        ingredients_data = [
            {"description": "浓缩咖啡", "text": "ESPRESSO", "body": [0.1, 0.05, 0.0, 1], "font": [1, 1, 1], "row": 0, "col": 0},
            {"description": "水", "text": "WATER", "body": [0.0, 0.4, 0.8, 1], "font": [1, 1, 1], "row": 0, "col": 1},
            {"description": "牛奶", "text": "MILK", "body": [1.0, 1.0, 1.0, 1], "font": [0, 0, 0], "row": 0, "col": 2},
            {"description": "香草", "text": "VANILLA", "body": [1.0, 0.9, 0.2, 1], "font": [0, 0, 0], "row": 1, "col": 0},
            {"description": "焦糖", "text": "CARAMEL", "body": [1.0, 0.5, 0.0, 1], "font": [0, 0, 0], "row": 1, "col": 1},
            {"description": "可可", "text": "CHOCO", "body": [0.6, 0.3, 0.1, 1], "font": [1, 1, 1], "row": 1, "col": 2},
            {"description": "燕麦奶", "text": "OAT", "body": [0.8, 0.7, 0.5, 1], "font": [0, 0, 0], "row": 2, "col": 0},
            {"description": "糖", "text": "SUGAR", "body": [0.7, 0.7, 0.7, 1], "font": [0, 0, 0], "row": 2, "col": 1},
            {"description": "冰", "text": "ICE", "body": [0.5, 0.9, 1.0, 1], "font": [0, 0, 0], "row": 2, "col": 2}
        ]

        bottle_w = 0.025
        bottle_h = 0.05
        self.bottle_records = []

        for item in ingredients_data:
            pos_x = (item["col"] - 1) * 0.2
            pos_y = shelf_start_y
            pos_z = table_h + 0.09 + (item["row"] * shelf_step_height) + bottle_h

            vis_shape = p.createVisualShape(p.GEOM_BOX, halfExtents=[bottle_w, bottle_w, bottle_h], rgbaColor=item["body"])
            col_shape = p.createCollisionShape(p.GEOM_BOX, halfExtents=[bottle_w, bottle_w, bottle_h])

            uid = p.createMultiBody(
                baseMass=1.0,
                baseCollisionShapeIndex=col_shape,
                baseVisualShapeIndex=vis_shape,
                basePosition=[pos_x, pos_y, pos_z]
            )

            p.addUserDebugText(
                text=item["text"], textPosition=[-0.1, -0.136, 0.02],
                textColorRGB=item["font"], textSize=1.4, parentObjectUniqueId=uid
            )

            self.bottle_records.append({
                "id": uid,
                "init_pos": [pos_x, pos_y, pos_z],
                "init_orn": [0, 0, 0, 1],
                "name": item["text"]
            })

        # 咖啡杯
        p.createMultiBody(
            baseMass=0.5,
            baseVisualShapeIndex=p.createVisualShape(p.GEOM_CYLINDER, radius=0.05, length=0.12, rgbaColor=[1, 1, 1, 1]),
            baseCollisionShapeIndex=p.createCollisionShape(p.GEOM_CYLINDER, radius=0.05, height=0.12),
            basePosition=[-0.4, -0.2, table_h + 0.08]
        )

        # 机械臂
        robot_start_pos = [-0.3, -0.65, table_h]
        robot_start_orn = p.getQuaternionFromEuler([0, 0, 0])
        self.robotId = p.loadURDF("franka_panda/panda.urdf", robot_start_pos, robot_start_orn, useFixedBase=True)

        # 设置机械臂初始姿态
        home_joints = [0.0, -0.24, 0.0, -2.0, 0.0, 1.8, 0.8]
        for i in range(7):
            p.resetJointState(self.robotId, i, home_joints[i])
        p.resetJointState(self.robotId, 9, 0.04)
        p.resetJointState(self.robotId, 10, 0.04)

    def _create_camera(self):
        """创建虚拟相机标记"""
        self.camera_pos = [0, -0.5, 1.3]
        p.createMultiBody(
            baseMass=0,
            baseVisualShapeIndex=p.createVisualShape(p.GEOM_BOX, halfExtents=[0.05, 0.02, 0.02], rgbaColor=[0, 1, 0, 1]),
            basePosition=self.camera_pos
        )

    def reset_scene(self):
        """重置场景到初始状态"""
        print(">>> 正在重置场景...")

        # 重置所有瓶子
        for record in self.bottle_records:
            p.resetBasePositionAndOrientation(record["id"], record["init_pos"], [0, 0, 0, 1])

        # 重置机械臂
        home_joints = [0.0, -0.24, 0.0, -2.0, 0.0, 1.8, 0.8]
        for i in range(7):
            p.resetJointState(self.robotId, i, home_joints[i])
            p.setJointMotorControl2(self.robotId, i, p.POSITION_CONTROL, targetPosition=home_joints[i], force=200)

        # 重置夹爪
        p.resetJointState(self.robotId, 9, 0.04)
        p.resetJointState(self.robotId, 10, 0.04)
        p.setJointMotorControl2(self.robotId, 9, p.POSITION_CONTROL, targetPosition=0.04, force=200)
        p.setJointMotorControl2(self.robotId, 10, p.POSITION_CONTROL, targetPosition=0.04, force=200)

        print(">>> 重置完成")

    def swap_bottles(self, idx1, idx2):
        """交换两个瓶子的位置"""
        if not (0 <= idx1 < len(self.bottle_records)) or not (0 <= idx2 < len(self.bottle_records)):
            print(f"❌ 索引错误：请输入 1-9 之间的数字")
            return

        print(f">>> 正在交换瓶子 {idx1+1} ({self.bottle_records[idx1]['name']}) 和 {idx2+1} ({self.bottle_records[idx2]['name']})...")

        id1 = self.bottle_records[idx1]["id"]
        id2 = self.bottle_records[idx2]["id"]

        pos1, orn1 = p.getBasePositionAndOrientation(id1)
        pos2, orn2 = p.getBasePositionAndOrientation(id2)

        p.resetBasePositionAndOrientation(id1, pos2, orn1)
        p.resetBasePositionAndOrientation(id2, pos1, orn2)
        print(">>> 交换完成")

    def _console_input_loop(self):
        """键盘监听循环：处理场景重置和瓶子交换指令"""
        print("\n" + "="*50)
        print("【指令说明】")
        print("输入 '0'  -> 重置场景")
        print("输入 '19' -> 交换第1个和第9个瓶子")
        print("..." + "="*50 + "\n")

        while self.running:
            try:
                cmd = input()

                if cmd == '0':
                    self.reset_scene()
                elif len(cmd) == 2 and cmd.isdigit():
                    idx1 = int(cmd[0]) - 1
                    idx2 = int(cmd[1]) - 1
                    if idx1 != idx2:
                        self.swap_bottles(idx1, idx2)
                    else:
                        print("无效操作")
                else:
                    print("无效指令。请输入 '0' 或两位数字")
            except Exception as e:
                print(f"输入处理错误: {e}")

    def run(self):
        """运行物理仿真循环"""
        try:
            while True:
                p.stepSimulation()
                time.sleep(1./240.)
        except KeyboardInterrupt:
            self.running = False
            print("程序退出")

if __name__ == "__main__":
    server = CoffeeShopServer()
    server.run()