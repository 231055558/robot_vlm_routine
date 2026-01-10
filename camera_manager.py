import pybullet as p
import matplotlib.pyplot as plt
import numpy as np
import math
import os

class CameraManager:
    def __init__(self, save_path="captured_scene.png"):
        self.save_path = save_path
        # 相机位置 (机器人后上方)
        self.camera_pos = [0, -0.5, 1.3]
        self.target_pos = [0, math.pi, 0]
        self.up_vector = [0, 0, 1]

    def capture_image(self):
        """拍摄并保存图片，返回图片路径"""
        try:
            # 检查连接状态，如果没有连接则尝试连接 (防止单独运行报错)
            if not p.isConnected():
                p.connect(p.SHARED_MEMORY)

            # 计算矩阵
            view_matrix = p.computeViewMatrix(
                cameraEyePosition=self.camera_pos,
                cameraTargetPosition=self.target_pos,
                cameraUpVector=self.up_vector
            )
            
            proj_matrix = p.computeProjectionMatrixFOV(
                fov=60, aspect=1.0, nearVal=0.1, farVal=100.0
            )

            print("📷 [摄像头] 正在捕获图像...")
            width, height, rgbImg, depthImg, segImg = p.getCameraImage(
                width=640,
                height=640,
                viewMatrix=view_matrix,
                projectionMatrix=proj_matrix,
                renderer=p.ER_BULLET_HARDWARE_OPENGL
            )

            # 处理图像
            rgb_array = np.array(rgbImg, dtype=np.uint8)
            rgb_array = rgb_array.reshape((height, width, 4))
            rgb_array = rgb_array[:, :, :3] # 去掉 Alpha 通道

            # 保存
            plt.imsave(self.save_path, rgb_array)
            print(f"📷 [摄像头] 图像已保存至: {self.save_path}")
            
            return self.save_path

        except Exception as e:
            print(f"❌ 摄像头捕获失败: {e}")
            return None

if __name__ == '__main__':
    cam = CameraManager()
    cam.capture_image()