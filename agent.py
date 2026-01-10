import time
import json
from camera_manager import CameraManager
from robot_controller import RobotController
from recipe_llm import RecipeLLM
from vision_llm import VisionLLM
from llm_planner_end2end import End2EndPlanner

class CoffeeAgent:
    """主控制器：协调视觉、语言模型和机械臂执行完整任务流程"""

    def __init__(self):
        print("🤖 正在初始化系统...")

        # 硬件接口
        self.camera = CameraManager()
        self.controller = RobotController()

        # AI 模型
        self.brain_recipe = RecipeLLM()       # 订单 -> 配方
        self.brain_vision = VisionLLM()       # 图像 -> 坐标
        self.brain_planner = End2EndPlanner() # 配方+坐标 -> 动作

        print("✅ 系统就绪！")

    def run(self):
        while True:
            print("\n" + "="*50)
            user_input = input("🗣️ 请输入您的需求 (输入 'q' 退出): ")
            
            if user_input.lower() == 'q':
                print("👋 再见！")
                break
            
            self._process_order(user_input)

    def _process_order(self, user_input):
        """处理订单全流程：配方 -> 视觉 -> 规划 -> 执行"""

        # [1/4] 生成配方
        print(f"\n[1/4] 分析订单: {user_input} ...")
        recipe_data = self.brain_recipe.generate_recipe(user_input)

        if not recipe_data:
            print("❌ 无法生成配方")
            return

        if recipe_data.get("status") == "reject":
            print(f"🚫 {recipe_data.get('message')}")
            return

        print(f"✅ {recipe_data['product_name']}")
        recipe_steps = recipe_data['steps']
        print(json.dumps(recipe_steps, indent=2, ensure_ascii=False))

        # [2/4] 视觉识别和库存核对
        print(f"\n[2/4] 视觉扫描...")
        image_path = self.camera.capture_image()
        if not image_path:
            return

        location_map = self.brain_vision.detect_ingredients(image_path)
        if not location_map:
            print("❌ 视觉识别失败")
            return

        # 核对原料库存
        missing_ingredients = []
        for step in recipe_steps:
            needed_item = step['ingredient']
            if needed_item not in location_map or not location_map[needed_item]:
                missing_ingredients.append(needed_item)

        if missing_ingredients:
            print(f"🚫 缺少原料: {missing_ingredients}")
            return
        else:
            print("✅ 库存充足")

        # [3/4] 动作规划
        print(f"\n[3/4] 生成运动轨迹...")
        full_action_plan = self.brain_planner.plan_recipe(recipe_steps, location_map)

        if not full_action_plan:
            print("❌ 动作规划失败")
            return

        print(f"✅ 轨迹规划完成，共 {len(full_action_plan)} 步")

        # [4/4] 执行动作
        print(f"\n[4/4] 执行动作...")
        self._execute_physical_actions(full_action_plan)
        print("\n🎉 制作完成！")

        # 回到安全位置
        self.controller.move_to_smooth([0, -0.4, 1.0], steps=100)

    def _execute_physical_actions(self, actions):
        """解析动作指令并执行：MOVE, GRAB, WRIST, WAIT"""
        total_steps = len(actions)
        for i, act in enumerate(actions):
            cmd = act.get("cmd")
            print(f"   [{i+1}/{total_steps}] {cmd}: {act}")

            if cmd == "MOVE":
                self.controller.move_to_smooth(act["pos"], steps=150)
            elif cmd == "GRAB":
                self.controller.grab(act["width"])
            elif cmd == "WRIST":
                self.controller.rotate_wrist(act["angle"], steps=100)
            elif cmd == "WAIT":
                time.sleep(act.get("time", 1.0))

if __name__ == "__main__":
    agent = CoffeeAgent()
    agent.run()