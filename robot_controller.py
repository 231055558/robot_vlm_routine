import pybullet as p
import time
import math

class RobotController:
    def __init__(self):
        # 连接到服务器
        try:
            self.client_id = p.connect(p.SHARED_MEMORY)
            if self.client_id < 0: raise Exception
        except:
            print("请先运行 coffee_server.py ！")
            exit()
            
        print("成功连接！")
        self.robotId = self._find_robot_id()
        self.end_effector_index = 11 

    def _find_robot_id(self):
        num = p.getNumBodies()
        for i in range(num):
            if "panda" in p.getBodyInfo(i)[1].decode("utf-8"):
                return i
        return None

    def get_current_joint_angles(self):
        """获取机械臂当前7个关节的角度"""
        if self.robotId is None: return [0]*7
        angles = []
        for i in range(7):
            angles.append(p.getJointState(self.robotId, i)[0])
        return angles

    def move_to_smooth(self, target_pos, steps=100, delay=0.01):
            """平滑移动函数 (带零空间约束和高精度IK，解决抖动问题)"""
            if self.robotId is None: return

            # 1. 定义 Franka 机械臂的物理限制 (这是解决乱动的关键)
            # ll: lower limits (关节下限)
            # ul: upper limits (关节上限)
            # jr: joint ranges (关节范围)
            # rp: rest poses (休息姿态 - 也就是我们希望它保持的舒适姿态)
            ll = [-2.96, -1.83, -2.96, -3.09, -2.96, -0.08, -2.96]
            ul = [ 2.96,  1.83,  2.96,  0.08,  2.96,  3.82,  2.96]
            jr = [ 5.92,  3.66,  5.92,  3.17,  5.92,  3.90,  5.92]
            rp = [0, -0.24, 0, -2, 0, 1.8, 0.8] # 这里的姿态和你初始化时的一致

            # 姿态：抓手垂直向下
            orn = p.getQuaternionFromEuler([math.pi, math.pi/2, -math.pi/2])
            
            # 2. 计算高精度 IK
            # maxNumIterations=100: 强制算100次，算准为止
            # residualThreshold=1e-5: 误差小于 0.00001 才算成功
            target_joints = p.calculateInverseKinematics(
                self.robotId, 
                self.end_effector_index, 
                target_pos, 
                orn,
                lowerLimits=ll,
                upperLimits=ul,
                jointRanges=jr,
                restPoses=rp,
                maxNumIterations=100,
                residualThreshold=1e-5
            )
            
            # 3. 获取起点关节角度
            start_joints = self.get_current_joint_angles()

            # 4. 插值循环 (你的逻辑保持不变)
            for step in range(steps):
                t = step / steps 
                current_command = []
                for i in range(7):
                    angle = start_joints[i] + (target_joints[i] - start_joints[i]) * t
                    current_command.append(angle)
                
                for i in range(7):
                    p.setJointMotorControl2(self.robotId, i, p.POSITION_CONTROL, targetPosition=current_command[i], force=200)
                time.sleep(delay)
            
            # 5. 锁定 (死死锁住算出来的那个解，不要再让物理引擎自己微调)
            for i in range(7):
                p.setJointMotorControl2(self.robotId, i, p.POSITION_CONTROL, targetPosition=target_joints[i], force=200)

    def grab(self, width=0.0, steps=50, delay=0.01):
        """平滑抓取"""
        if self.robotId is None: return
        start_width = p.getJointState(self.robotId, 9)[0]
        for step in range(steps):
            t = step / steps
            current_width = start_width + (width - start_width) * t
            p.setJointMotorControl2(self.robotId, 9, p.POSITION_CONTROL, targetPosition=current_width, force=20)
            p.setJointMotorControl2(self.robotId, 10, p.POSITION_CONTROL, targetPosition=current_width, force=20)
            time.sleep(delay)
        p.setJointMotorControl2(self.robotId, 9, p.POSITION_CONTROL, targetPosition=width, force=60)
        p.setJointMotorControl2(self.robotId, 10, p.POSITION_CONTROL, targetPosition=width, force=60)
        time.sleep(0.2)

    # --- 新增功能：直接旋转手腕 (J7) ---
    def rotate_wrist(self, angle_deg, steps=100, delay=0.01):
        """
        在当前姿态基础上，旋转手腕 (Joint 6)
        :param angle_deg: 旋转角度 (度)，正数顺时针，负数逆时针。例如 90 或 -90
        """
        if self.robotId is None: return
        
        print(f">>> 正在旋转手腕 {angle_deg} 度...")

        # 1. 获取当前所有关节角度 (作为起点)
        start_joints = self.get_current_joint_angles()
        
        # 2. 设定目标关节角度
        target_joints = list(start_joints) # 复制一份
        
        # 3. 只修改第 7 个关节 (索引 6)
        # 将角度转为弧度
        rotation_rad = math.radians(angle_deg)
        target_joints[6] += rotation_rad # 在当前角度基础上增加

        # 4. 插值执行
        for step in range(steps):
            t = step / steps 
            current_command = []
            for i in range(7):
                # 线性插值
                angle = start_joints[i] + (target_joints[i] - start_joints[i]) * t
                current_command.append(angle)
            
            for i in range(7):
                p.setJointMotorControl2(self.robotId, i, p.POSITION_CONTROL, targetPosition=current_command[i], force=200)
            time.sleep(delay)
            
        # 5. 锁定位置
        for i in range(7):
            p.setJointMotorControl2(self.robotId, i, p.POSITION_CONTROL, targetPosition=target_joints[i], force=200)


# --- 测试控制 ---
if __name__ == "__main__":
    controller = RobotController()
    
    print(">>> 1. 打开夹爪...")
    controller.grab(0.04)
    time.sleep(0.2)

    # 移动到工作位置
    print(">>> 2. 移动工作位置...")
    controller.move_to_smooth([0, -0.05, 1.0], steps=100)
    time.sleep(0.2)


    # 移动到抓取位置 (Milk)
    print(">>> 2. 移动到牛奶瓶前...")
    controller.move_to_smooth([0.2, -0.05, 0.8+0.15*0], steps=300)
    time.sleep(0.2)

    # 移动到抓取位置 (Milk)
    print(">>> 2. 移动到牛奶瓶...")
    controller.move_to_smooth([0.2, 0.085, 0.8+0.15*0], steps=150)
    time.sleep(0.2)
    
    print(">>> 3. 抓取...")
    controller.grab(0.0)
    time.sleep(0.2)

    print(">>> 4. 提起...")
    controller.move_to_smooth([0.2, -0.05, 0.8+0.15*0], steps=100)

    # 移动到工作位置
    print(">>> 2. 移动工作位置...")
    controller.move_to_smooth([0, -0.05, 1.0], steps=100)
    time.sleep(0.2)

    print(">>> 5. 移动到杯子上方...")
    # 把杯子位置稍微抬高一点，给倒水留空间
    controller.move_to_smooth([-0.35+0.05, -0.2, 1.0], steps=300)
    time.sleep(0.5)

    # --- 核心：直接旋转关节倒水 ---
    # 旋转 90 度
    controller.rotate_wrist(-90, steps=100)
    
    print(">>> (正在倒水...)")
    time.sleep(1.0) # 保持倒水姿态

    # --- 回正 ---
    # 旋转 -90 度 (回到原来的位置)
    print(">>> 6. 回正...")
    controller.rotate_wrist(90, steps=100)
    time.sleep(0.5)

    # 移动到工作位置
    print(">>> 2. 移动工作位置...")
    controller.move_to_smooth([0, -0.05, 1.0], steps=100)
    time.sleep(0.2)

    print(">>> 7. 放回原处...")
    # controller.move_to_smooth([0.25+0.01, 0.0, 0.8], steps=300)
    controller.move_to_smooth([0.2, -0.05, 0.8+0.15*0], steps=150)
    controller.move_to_smooth([0.2, 0.085, 0.8+0.15*0], steps=150)
    controller.grab(0.04)
    controller.move_to_smooth([0.2, -0.05, 0.8+0.15*0], steps=150)

    
    
    # 回到安全位置
    controller.move_to_smooth([0, -0.2, 1.0], steps=100)

    print("测试结束")