import pybullet as p
import time
import math

class RobotController:
    """机械臂控制器：执行 IK 计算和关节运动控制"""

    def __init__(self):
        # 连接到仿真服务器
        try:
            self.client_id = p.connect(p.SHARED_MEMORY)
            if self.client_id < 0:
                raise Exception
        except:
            print("❌ 请先运行 coffee_env.py")
            exit()

        print("✅ 连接成功")
        self.robotId = self._find_robot_id()
        self.end_effector_index = 11

    def _find_robot_id(self):
        """查找 Franka Panda 机械臂的 ID"""
        num = p.getNumBodies()
        for i in range(num):
            if "panda" in p.getBodyInfo(i)[1].decode("utf-8"):
                return i
        return None

    def get_current_joint_angles(self):
        """获取机械臂当前7个关节的角度"""
        if self.robotId is None:
            return [0]*7
        angles = []
        for i in range(7):
            angles.append(p.getJointState(self.robotId, i)[0])
        return angles

    def move_to_smooth(self, target_pos, steps=100, delay=0.01):
        """平滑移动到目标位置（带零空间约束和高精度IK）"""
        if self.robotId is None:
            return

        # Franka 机械臂物理限制
        ll = [-2.96, -1.83, -2.96, -3.09, -2.96, -0.08, -2.96]
        ul = [ 2.96,  1.83,  2.96,  0.08,  2.96,  3.82,  2.96]
        jr = [ 5.92,  3.66,  5.92,  3.17,  5.92,  3.90,  5.92]
        rp = [0, -0.24, 0, -2, 0, 1.8, 0.8]

        # 姿态：抓手垂直向下
        orn = p.getQuaternionFromEuler([math.pi, math.pi/2, -math.pi/2])

        # 高精度 IK 计算
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

        # 平滑插值
        start_joints = self.get_current_joint_angles()
        for step in range(steps):
            t = step / steps
            current_command = []
            for i in range(7):
                angle = start_joints[i] + (target_joints[i] - start_joints[i]) * t
                current_command.append(angle)

            for i in range(7):
                p.setJointMotorControl2(self.robotId, i, p.POSITION_CONTROL, targetPosition=current_command[i], force=200)
            time.sleep(delay)

        # 锁定最终位置
        for i in range(7):
            p.setJointMotorControl2(self.robotId, i, p.POSITION_CONTROL, targetPosition=target_joints[i], force=200)

    def grab(self, width=0.0, steps=50, delay=0.01):
        """平滑抓取/释放（控制夹爪开合）"""
        if self.robotId is None:
            return
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

    def rotate_wrist(self, angle_deg, steps=100, delay=0.01):
        """旋转手腕（Joint 6）指定角度"""
        if self.robotId is None:
            return

        # 获取当前关节角度
        start_joints = self.get_current_joint_angles()
        target_joints = list(start_joints)

        # 修改第 7 个关节（索引 6）
        rotation_rad = math.radians(angle_deg)
        target_joints[6] += rotation_rad

        # 平滑插值
        for step in range(steps):
            t = step / steps
            current_command = []
            for i in range(7):
                angle = start_joints[i] + (target_joints[i] - start_joints[i]) * t
                current_command.append(angle)

            for i in range(7):
                p.setJointMotorControl2(self.robotId, i, p.POSITION_CONTROL, targetPosition=current_command[i], force=200)
            time.sleep(delay)

        # 锁定位置
        for i in range(7):
            p.setJointMotorControl2(self.robotId, i, p.POSITION_CONTROL, targetPosition=target_joints[i], force=200)

if __name__ == "__main__":
    # 测试控制
    controller = RobotController()

    print(">>> 测试：抓取和倒水动作")
    controller.grab(0.04)
    time.sleep(0.2)

    controller.move_to_smooth([0, -0.05, 1.0], steps=100)
    controller.move_to_smooth([0.2, -0.05, 0.8], steps=150)
    controller.move_to_smooth([0.2, 0.085, 0.8], steps=150)

    controller.grab(0.0)
    time.sleep(0.2)

    controller.move_to_smooth([0.2, -0.05, 0.8], steps=100)
    controller.move_to_smooth([0, -0.05, 1.0], steps=100)
    controller.move_to_smooth([-0.3, -0.2, 1.0], steps=150)

    controller.rotate_wrist(-90, steps=100)
    time.sleep(1.0)
    controller.rotate_wrist(90, steps=100)

    controller.move_to_smooth([0, -0.05, 1.0], steps=100)
    controller.move_to_smooth([0.2, -0.05, 0.8], steps=150)
    controller.move_to_smooth([0.2, 0.085, 0.8], steps=150)
    controller.grab(0.04)
    controller.move_to_smooth([0.2, -0.05, 0.8], steps=150)
    controller.move_to_smooth([0, -0.2, 1.0], steps=100)

    print(">>> 测试结束")