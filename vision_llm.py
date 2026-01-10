import os
import json
import base64
import mimetypes
from pathlib import Path
from zai import ZhipuAiClient
from dotenv import load_dotenv

load_dotenv()

# 视觉专家的核心知识库
INGREDIENT_FEATURES = """
1. **ESPRESSO** (浓缩咖啡): 深黑褐色/黑色瓶子。
2. **WATER** (水): 鲜艳的深蓝色瓶子。
3. **MILK** (牛奶): 纯白色瓶子。
4. **VANILLA** (香草): 鲜亮的柠檬黄色瓶子。
5. **CARAMEL** (焦糖): 鲜艳的橙色瓶子。
6. **CHOCO** (可可/巧克力): 红棕色/砖红色瓶子。
7. **OAT** (燕麦奶): 沙色/卡其色/米黄色瓶子。
8. **SUGAR** (糖): 浅灰色/银色瓶子。
9. **ICE** (冰): 浅青色/天蓝色(比水浅)瓶子。
"""

SYSTEM_PROMPT = f"""
你是一个基于视觉的【咖啡厅库存盘点专家】。
你看到的图片是一个 **3行 x 3列** 的阶梯货架，上面摆放着 9 个方形瓶子。
- **前排 (Row 0)**: 最靠近下方/镜头的一排。
- **中排 (Row 1)**: 中间的一排。
- **后排 (Row 2)**: 最远/最高的一排。
- **列 (Col)**: 从左到右依次为 0, 1, 2。

### 你的任务
请根据以下【原料颜色特征表】，识别图片中每个位置放的是什么原料。
{INGREDIENT_FEATURES}

### 输出要求
请直接返回一个 JSON 对象，键为原料的英文标准名称 (如 "ESPRESSO", "MILK")，值为它在货架上的坐标 `[row, col]`。
如果不确定某个位置，可以跳过，但必须保证识别出的物体准确。

**JSON 样例:**
{{
  "ESPRESSO": [0, 0],
  "MILK": [0, 2],
  "CARAMEL": [1, 1],
  ...
}}
"""

class VisionLLM:
    """视觉识别器：基于 VLM 识别图像中的原料位置"""

    def __init__(self):
        self.api_key = os.getenv("ZHIPUAI_API_KEY")
        if not self.api_key:
            raise ValueError("❌ 错误：未设置 ZHIPUAI_API_KEY")
        self.client = ZhipuAiClient(api_key=self.api_key)

    def _encode_image(self, image_path):
        """将图像编码为 Base64"""
        if not image_path.exists():
            return None
        mime_type, _ = mimetypes.guess_type(image_path)
        if mime_type is None:
            mime_type = "application/octet-stream"
        with open(image_path, "rb") as image_file:
            base64_data = base64.b64encode(image_file.read()).decode('utf-8')
        return f"data:{mime_type};base64,{base64_data}"

    def detect_ingredients(self, image_path_str: str):
        """识别图像中的原料位置"""
        print(f"👁️ 视觉感知中...")

        base64_url = self._encode_image(Path(image_path_str))
        if not base64_url:
            print("❌ 图片加载失败")
            return None

        try:
            response = self.client.chat.completions.create(
                model="glm-4.6v-flash",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": SYSTEM_PROMPT},
                            {"type": "image_url", "image_url": {"url": base64_url}}
                        ]
                    }
                ],
                temperature=0.1,
                top_p=0.5,
            )

            content = response.choices[0].message.content

            # 清理 Markdown 代码块
            if "```" in content:
                content = content.replace("```json", "").replace("```", "")

            location_map = json.loads(content)
            print("✅ 视觉识别成功")
            return location_map

        except Exception as e:
            print(f"❌ 视觉识别失败: {e}")
            return None

if __name__ == "__main__":
    eye = VisionLLM()
    image_file = "captured_scene.png"

    if os.path.exists(image_file):
        result = eye.detect_ingredients(image_file)
        print(json.dumps(result, indent=2, ensure_ascii=False))

        if result and result.get("ESPRESSO") == [0, 0]:
            print("\n🎉 测试通过")
        else:
            print("\n⚠️ 识别结果可能有误")
    else:
        print(f"❌ 请先运行 camera_manager.py 生成 {image_file}")