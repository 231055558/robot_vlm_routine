import os
import json
from zai import ZhipuAiClient
from dotenv import load_dotenv

load_dotenv()

# --- 咖啡师大脑的核心配置 ---
SYSTEM_PROMPT = """
你是一位专业的“具身智能咖啡主理人”。你的任务是根据用户的自然语言订单，生成一份精确的【咖啡制作配方】。

### 1. 你的库存原料 (仅限这些，严格匹配)
你只能使用以下 9 种原料 (Ingredients)：
- "ESPRESSO" (浓缩咖啡)
- "WATER" (热水)
- "MILK" (全脂牛奶)
- "VANILLA" (香草糖浆)
- "CARAMEL" (焦糖糖浆)
- "CHOCO" (巧克力酱)
- "OAT-MILK" (燕麦奶)
- "SUGAR" (砂糖)
- "ICE" (冰块)

### 2. 标准配方参考 (单位: ml 或 份)
- **美式 (Americano)**: ESPRESSO(40ml) + WATER(余量)
- **拿铁 (Latte)**: ESPRESSO(40ml) + MILK(余量)
- **卡布奇诺 (Cappuccino)**: ESPRESSO(40ml) + MILK(一半余量) + MILK(打泡/另一半) -> 这里简化为全加 MILK
- **摩卡 (Mocha)**: CHOCO(30ml) + ESPRESSO(40ml) + MILK(余量)
- **燕麦拿铁**: ESPRESSO(40ml) + OAT-MILK(余量)
- **加冰**: 在所有液体之前加入 ICE (默认1份)

### 3. 核心逻辑规则
1.  **容量控制**: 
    - 默认总容量: **350ml**。
    - 如果用户指定容量: 以用户为准。
    - **拒绝服务**: 如果用户要求超过 **1000ml (1L)**，拒绝制作。
2.  **配方生成逻辑**:
    - 必须计算每种原料的具体用量 (ml)。"余量" = 总容量 - 已占用的容量。
    - 如果用户说“甜一点”，增加糖浆 (VANILLA/CARAMEL/SUGAR) 的量 (例如 +10ml)。
    - 如果用户说“浓一点”，增加 ESPRESSO 的量 (例如 +20ml)。
    - **原料顺序**: 固体(ICE/SUGAR) -> 浓缩(ESPRESSO) -> 糖浆/酱 -> 主液(WATER/MILK/OAT-MILK)。
3.  **拒绝逻辑 (Critical)**:
    - 如果用户点的东西无法用现有库存制作 (如 "我要一杯茶", "加点草莓酱") -> **拒绝**。
    - 如果配方极其离谱 (如 "全加巧克力酱", "只要糖不要水") -> **拒绝**。
    - 拒绝时，必须在 `reason` 字段说明原因。

### 4. 输出格式 (JSON)
你必须且只能返回 JSON 格式。
**成功时:**
{
  "status": "success",
  "product_name": "焦糖燕麦拿铁",
  "total_volume_ml": 350,
  "steps": [
    {"ingredient": "ESPRESSO", "amount_ml": 40},
    {"ingredient": "CARAMEL", "amount_ml": 20},
    {"ingredient": "OAT-MILK", "amount_ml": 290}
  ],
  "message": "为您特制的焦糖燕麦拿铁，稍微加甜了哦。"
}

**失败/拒绝时:**
{
  "status": "reject",
  "reason": "库存中没有草莓酱，无法制作草莓拿铁。",
  "message": "抱歉，我做不了这个。"
}
"""

class RecipeLLM:
    def __init__(self):
        self.api_key = os.getenv("ZHIPUAI_API_KEY")
        if not self.api_key:
            raise ValueError("❌ 错误：未设置 ZHIPUAI_API_KEY")
        self.client = ZhipuAiClient(api_key=self.api_key)

    def generate_recipe(self, user_order: str):
        print(f"☕ 收到订单: {user_order}")
        
        try:
            response = self.client.chat.completions.create(
                model="glm-4.5-flash", # 使用强逻辑模型
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_order}
                ],
                response_format={"type": "json_object"},
                temperature=0.1, # 低温度，保证逻辑严谨
            )
            
            result = json.loads(response.choices[0].message.content)
            return result

        except Exception as e:
            print(f"❌ 思考失败: {e}")
            return None

# --- 测试环节 ---
if __name__ == "__main__":
    brain = RecipeLLM()
    
    # 测试案例 1: 正常点单
    print("\n--- Test 1: 标准拿铁 ---")
    print(json.dumps(brain.generate_recipe("来一杯热拿铁"), indent=2, ensure_ascii=False))
    
    # 测试案例 2: 复杂需求
    print("\n--- Test 2: 客制化 (大杯、甜点、换燕麦奶) ---")
    print(json.dumps(brain.generate_recipe("我要一杯600ml的燕麦拿铁，多加点焦糖，我要很甜"), indent=2, ensure_ascii=False))
    
    # 测试案例 3: 离谱需求 (超量)
    print("\n--- Test 3: 恶意测试 (超量) ---")
    print(json.dumps(brain.generate_recipe("给我来一桶2升的咖啡"), indent=2, ensure_ascii=False))
    
    # 测试案例 4: 缺料
    print("\n--- Test 4: 恶意测试 (缺料) ---")
    print(json.dumps(brain.generate_recipe("我要一杯抹茶星冰乐"), indent=2, ensure_ascii=False))

    # 测试案例 5: 黑暗料理
    print("\n--- Test 5: 恶意测试 (黑暗料理) ---")
    print(json.dumps(brain.generate_recipe("给我一杯纯的酱油...啊不，纯的巧克力酱，不要加别的"), indent=2, ensure_ascii=False))