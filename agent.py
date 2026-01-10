import time
import json
import os

# --- 导入所有模块 ---
from camera_manager import CameraManager
from robot_controller import RobotController
from recipe_llm import RecipeLLM
from vision_llm import VisionLLM
from llm_planner_end2end import End2EndPlanner

class CoffeeAgent:
    def __init__(self):
        print("🤖 [Agent] 正在初始化所有子系统...")
        
        # 1. 硬件/底层接口
        self.camera = CameraManager()
        self.controller = RobotController() # 连接 PyBullet
        
        # 2. 三大 LLM 大脑
        self.brain_recipe = RecipeLLM()       # Level 1: 订单 -> 配方
        self.brain_vision = VisionLLM()       # Level 2: 图片 -> 坐标
        self.brain_planner = End2EndPlanner() # Level 3: 配方+坐标 -> 动作序列
        
        print("✅ [Agent] 系统就绪！等待指令。")

    def run(self):
        while True:
            print("\n" + "="*50)
            user_input = input("🗣️ 请输入您的需求 (输入 'q' 退出): ")
            
            if user_input.lower() == 'q':
                print("👋 再见！")
                break
            
            self._process_order(user_input)

    def _process_order(self, user_input):
        # ==========================================
        # STEP 1: 订单理解与配方生成
        # ==========================================
        print(f"\n[1/4] 正在分析订单: {user_input} ...")
        recipe_data = self.brain_recipe.generate_recipe(user_input)
        
        if not recipe_data:
            print("❌ 无法生成配方，流程结束。")
            return

        # 检查是否拒绝服务
        if recipe_data.get("status") == "reject":
            print(f"🚫 拒绝服务: {recipe_data.get('reason')}")
            print(f"🤖 回复: {recipe_data.get('message')}")
            return

        print(f"✅ 配方确认: {recipe_data['product_name']}")
        recipe_steps = recipe_data['steps'] # List of {ingredient, amount}
        print(json.dumps(recipe_steps, indent=2, ensure_ascii=False))

        # ==========================================
        # STEP 2: 视觉感知与库存核对
        # ==========================================
        print(f"\n[2/4] 正在进行视觉扫描...")
        # 1. 拍照
        image_path = self.camera.capture_image()
        if not image_path: return

        # 2. 视觉识别
        location_map = self.brain_vision.detect_ingredients(image_path)
        if not location_map:
            print("❌ 视觉识别失败，无法定位原料。")
            return
        
        print(f"👁️ 库存地图: {location_map}")

        # 3. 核心逻辑：核对配方原料是否存在
        print("🔍 正在核对原料库存...")
        missing_ingredients = []
        for step in recipe_steps:
            needed_item = step['ingredient']
            # 检查原料是否在地图里，且坐标不为空
            if needed_item not in location_map or not location_map[needed_item]:
                missing_ingredients.append(needed_item)
        
        if missing_ingredients:
            print(f"🚫 制作中断！缺少以下原料: {missing_ingredients}")
            print("请补充原料后重试。")
            return
        else:
            print("✅ 原料核对通过，库存充足。")

        # ==========================================
        # STEP 3: 动作规划 (End-to-End)
        # ==========================================
        print(f"\n[3/4] 正在生成机械臂运动轨迹...")
        
        # 调用 Level 3 LLM，传入配方和刚才看到的地图
        # 它会分步调用 API，生成一个完整的动作列表
        full_action_plan = self.brain_planner.plan_recipe(recipe_steps, location_map)
        
        if not full_action_plan:
            print("❌ 动作规划失败，无法生成指令。")
            return
            
        print(f"✅ 轨迹规划完成，共 {len(full_action_plan)} 步动作。")

        # ==========================================
        # STEP 4: 物理执行
        # ==========================================
        print(f"\n[4/4] 开始执行物理动作...")
        self._execute_physical_actions(full_action_plan)
        print("\n🎉 制作完成！请享用您的咖啡。")
        
        # 制作完成后，让机械臂回安全位置
        self.controller.move_to_smooth([0, -0.4, 1.0], steps=100)

    def _execute_physical_actions(self, actions):
        """
        解析 JSON 指令并驱动 RobotController
        """
        total_steps = len(actions)
        for i, act in enumerate(actions):
            cmd = act.get("cmd")
            print(f"   -> [{i+1}/{total_steps}] {cmd}: {act}")

            if cmd == "MOVE":
                # 使用 steps=150 (根据你的测试，这个速度比较稳)
                self.controller.move_to_smooth(act["pos"], steps=150)
                
            elif cmd == "GRAB":
                # 抓取用默认参数
                self.controller.grab(act["width"])
                
            elif cmd == "WRIST":
                # 旋转手腕，steps=100
                self.controller.rotate_wrist(act["angle"], steps=100)
                
            elif cmd == "WAIT":
                t = act.get("time", 1.0)
                time.sleep(t)
            
            # 动作间微小缓冲
            # time.sleep(0.05)

if __name__ == "__main__":
    # 启动 Agent
    agent = CoffeeAgent()
    agent.run()