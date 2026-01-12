# 具身智能咖啡机械臂仿真系统

一个展示大型语言模型（LLM）与视觉语言模型（VLM）驱动的具身智能机械臂的最小化案例，实现从自然语言订单到物理执行的端到端流程。

## 系统架构

```
用户订单
   ↓
[Recipe LLM] → 生成咖啡配方
   ↓
[Camera] → 拍摄当前场景
   ↓
[Vision LLM] → 识别原料位置
   ↓
[Motion Planner] → 生成运动轨迹
   ↓
[Robot Controller] → 执行物理动作
```

## 环境配置

### 系统要求
- Python 3.10
- PyBullet 物理引擎（机械臂仿真）

### 安装依赖

使用 conda 创建环境：

```bash
conda create -n robot_vlm python=3.10 -y
conda activate robot_vlm
```

安装依赖包：

```bash
pip install pybullet
pip install matplotlib
pip install numpy
pip install zai-sdk
pip install python-dotenv
```

### API 密钥配置

在项目根目录创建 `.env` 文件，获取智谱 AI API 密钥：

```
ZHIPUAI_API_KEY="your_zai_api_key"
```

> 获取方式：访问 [智谱 AI 开放平台](https://bigmodel.cn/) 注册并获取 API 密钥

## 程序说明

### 核心文件

| 文件 | 功能 | 说明 |
|------|------|------|
| `agent.py` | 主控制器 | 协调各子系统完成端到端流程 |
| `recipe_llm.py` | 配方生成 | 用 LLM 将自然语言订单转化为配方 |
| `vision_llm.py` | 视觉识别 | 用 VLM 识别图像中各原料的位置 |
| `llm_planner_end2end.py` | 运动规划 | 用 LLM 生成机械臂动作序列 |
| `robot_controller.py` | 机械臂控制 | 执行 IK 计算和关节控制 |
| `camera_manager.py` | 虚拟相机 | 在仿真环境中捕获图像 |
| `coffee_env.py` | 仿真场景服务器 | 初始化 PyBullet 仿真环境，管理场景状态 |

### 辅助文件

| 文件 | 功能 |
|------|------|
| `pybullet_test.py` | 基础 PyBullet 示例（可选参考） |

## 使用流程

### 1. 启动仿真环境

```bash
python coffee_env.py
```

这会启动一个 PyBullet 图形化窗口，包含：
- Franka Panda 机械臂
- 9 个原料瓶子（3×3 货架）
- 1 个咖啡杯

**场景指令说明：**
- 输入 `0` → 重置场景到初始状态
- 输入 `19` → 交换第1个和第9个瓶子（例如测试库存变化）

### 2. 启动 Agent 主程序（新终端）

```bash
python agent.py
```

按照提示输入自然语言订单，例如：
```
🗣️ 请输入您的需求: 来一杯热拿铁
```

Agent 会自动完成以下步骤：

**[1/4] 订单理解** → 生成配方
**[2/4] 视觉感知** → 识别原料位置并核对库存
**[3/4] 动作规划** → 计算机械臂轨迹
**[4/4] 物理执行** → 控制机械臂执行动作

## 主要概念

### 坐标系
- **全局工作点 (Work Pose)**: `[0, -0.2, 1.0]` - 机械臂的安全待命位置
- **倒水点 (Cup Pose)**: `[-0.3, -0.2, 1.0]` - 杯子上方位置
- **货架坐标**：通过 row（行）和 col（列）编码，自动转换为实际 (x, y, z)

### 原料列表
机械臂库存中有 9 种原料，分别是：
1. **ESPRESSO** (浓缩咖啡) - 深棕色
2. **WATER** (热水) - 深蓝色
3. **MILK** (牛奶) - 白色
4. **VANILLA** (香草糖浆) - 黄色
5. **CARAMEL** (焦糖糖浆) - 橙色
6. **CHOCO** (巧克力酱) - 红棕色
7. **OAT** (燕麦奶) - 米黄色
8. **SUGAR** (砂糖) - 灰色
9. **ICE** (冰块) - 浅青色
