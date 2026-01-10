import os
import json
import re
from zai import ZhipuAiClient
from dotenv import load_dotenv

load_dotenv()

# --- 核心 Prompt：纯粹的坐标计算与逻辑 ---
END2END_PROMPT = """
你是一个精通机械臂控制的数学家。你的任务是为【指定原料】生成动作序列。

### 1. 全局固定坐标 (Global Poses)
- **Work Pose (工作点)**: `[0, -0.2, 1.0]`
- **Cup Pose (倒水点)**: `[-0.3, -0.2, 1.0]`

### 2. 目标坐标计算公式 (Input: Grid [row, col])
你需要根据 grid 计算出目标瓶子的 X 和 Z：
- **Target_X**: `(col - 1) * 0.2`
  - (例: col=0 -> -0.2; col=1 -> 0.0; col=2 -> 0.2)
- **Target_Z**: `0.8 + (row * 0.15)`
  - (例: row=0 -> 0.8; row=1 -> 0.95; row=2 -> 1.1)

### 3. Y轴关键位置 (固定值)
- **Pre_Y (准备/后退点)**: `-0.05`
- **Grasp_Y (抓取/接触点)**: `0.090`

### 4. 必须生成的动作序列 (SOP)
**规则**：严禁垂直提起。取放过程必须是 Y 轴方向的**水平平移**。

1. `MOVE` to Work Pose.
2. `MOVE` to Pre-Grasp: `[Target_X, Pre_Y, Target_Z]`
3. `MOVE` to Grasp: `[Target_X, Grasp_Y, Target_Z]` (前伸)
4. `GRAB` (Close, width=0.0).
5. `MOVE` to Pre-Grasp: `[Target_X, Pre_Y, Target_Z]` (后退)
6. `MOVE` to Work Pose.
7. `MOVE` to Cup Pose.
8. `WRIST` (-90) -> `WAIT` (time) -> `WRIST` (90).
9. `MOVE` to Work Pose.
10. `MOVE` to Pre-Grasp: `[Target_X, Pre_Y, Target_Z]`
11. `MOVE` to Grasp: `[Target_X, Grasp_Y, Target_Z]` (前伸)
12. `GRAB` (Open, width=0.04).
13. `MOVE` to Pre-Grasp: `[Target_X, Pre_Y, Target_Z]` (后退)
14. `MOVE` to Work Pose.

*注：WAIT time = amount_ml / 50。*

### 输出格式 (JSON List)
只输出指令，不要任何多余字段。
[
  {"cmd": "MOVE", "pos": [0.2, -0.05, 0.8]},
  {"cmd": "GRAB", "width": 0.0},
  {"cmd": "WRIST", "angle": -90},
  {"cmd": "WAIT", "time": 4.0}
]
"""

class End2EndPlanner:
    def __init__(self):
        self.api_key = os.getenv("ZHIPUAI_API_KEY")
        self.client = ZhipuAiClient(api_key=self.api_key)

    def _clean_json(self, text):
        text = re.sub(r"```json|```", "", text)
        start = text.find('['); end = text.rfind(']')
        return text[start:end+1] if start != -1 else "[]"

    def plan_ingredient(self, name, amount, grid):
        """为单个原料生成全套动作"""
        user_input = json.dumps({
            "target": name,
            "grid": grid,
            "amount_ml": amount
        })
        
        print(f"🤖 [AI计算] {name} (Grid {grid})...")
        
        try:
            response = self.client.chat.completions.create(
                model="glm-4.5-flash",
                messages=[
                    {"role": "system", "content": END2END_PROMPT},
                    {"role": "user", "content": user_input}
                ],
                temperature=0.01,
                timeout=30
            )
            content = self._clean_json(response.choices[0].message.content)
            return json.loads(content)
        except Exception as e:
            print(f"❌ 计算失败: {e}")
            return []

    def plan_recipe(self, recipe, location_map):
        full_plan = []
        
        # --- 修改：移除了这里手写的初始动作，完全信任 AI 的第一步 ---
        # 既然 AI 的 SOP 第一步就是去 Work Pose，这里就不需要加了
        
        for step in recipe:
            name = step['ingredient']
            amount = step['amount_ml']
            grid = location_map.get(name)
            
            if not grid:
                print(f"⚠️ 找不到 {name}，跳过")
                continue
            
            actions = self.plan_ingredient(name, amount, grid)
            if actions:
                full_plan.extend(actions)
            else:
                print(f"⚠️ {name} 动作生成失败")

        return full_plan

if __name__ == "__main__":
    planner = End2EndPlanner()
    
    mock_recipe = [
        {"ingredient": "ESPRESSO", "amount_ml": 40},
        {"ingredient": "MILK", "amount_ml": 200}
    ]
    mock_map = {
        "ESPRESSO": [0, 0],
        "MILK": [0, 2]
    }
    
    final_plan = planner.plan_recipe(mock_recipe, mock_map)
    
    with open("robot_plan.json", "w") as f:
        json.dump(final_plan, f, indent=2)
        
    print(f"\n✅ 计划生成完毕！共 {len(final_plan)} 步。")
    print(json.dumps(final_plan[:5], indent=2))