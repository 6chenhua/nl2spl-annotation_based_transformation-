"""ConsoleUI 交互式示例

此示例演示如何使用 ConsoleUI 进行交互式冲突解决。
当 Pipeline 检测到冲突时，会在终端显示问题并等待用户输入。

适用场景:
- 命令行工具
- Jupyter Notebook
- 开发调试
- 需要人工决策的转换任务
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.pipeline import Pipeline
from src.clarification.clarification_ui import ConsoleUI
from src.output_manager import OutputManager


async def main():
    """ConsoleUI 交互式示例"""

    print("=" * 80)
    print("ConsoleUI 模式示例 - 交互式冲突解决")
    print("=" * 80)
    print("\n此示例将在终端显示冲突澄清问题，需要您手动输入选择。\n")

    # 创建 Pipeline，使用 ConsoleUI 进行交互式提问
    # ConsoleUI 会在终端显示问题并等待键盘输入
    ui = ConsoleUI()

    # 配置输出到项目根目录的 output/ 文件夹
    config = {
        'output': {
            'enabled': True,
            'base_dir': '../output',  # 相对于 examples/ 目录
            'case_name': 'dispatcher_example',
            'save_intermediate': True,
            'pretty_print': True
        }
    }

    output_manager = OutputManager(case_name='dispatcher_example')
    pipeline = Pipeline(ui=ui, config=config, output_manager=output_manager)

    # 示例 prompt - 故意设计得模糊以产生冲突
    prompt = """
## 🎯 智能体调度系统提示词

你是一个智能体调度系统，负责根据 **当前流程（process）** 和 **用户聊天内容**，判断该调用哪个子智能体。

你不直接回复用户，只负责输出一个数字：

* **1 = 智能体A（图文执行助手）**
* **2 = 智能体B（视频执行助手）**
* **3 = 对博图文修改智能体（图文修改/反馈）**
* **4 = 对博视频修改智能体（视频修改/反馈）**

---

### 📊 智能体定义

#### **1 = 智能体A（图文执行助手，当`type == 视频`时不能选择）**

* **角色定位**：MCN 品牌执行专员，负责图文合作项目的执行对接。
* **核心职责**：

  1. 向博主传达图文类合作要求（大纲 → 初稿 → 发布）；
  2. 跟进稿件创作、初稿提交、发布节点；
  3. 收集博主提供的图文稿件和发布时间链接；
  4. 高情商沟通，督促时间节点。
* **典型场景**：

  * process 在 "稿件大纲创作中"、"博主大纲审核中"、"稿件大纲纠错中"、"客户大纲审核中"、"发布监控中" 等与图文稿件相关阶段。

---

#### **2 = 智能体B（视频执行助手，当`type == 图文`时不能选择）**

* **角色定位**：MCN 品牌执行专员，负责视频合作项目的执行对接。
* **核心职责**：

  1. 传达视频合作通知（大纲 → 脚本 → 初稿 → 预览 → 发布）；
  2. 提供飞书文档链接，供博主进行大纲/脚本创作或修改；
  3. 收集博主提供的视频预览/发布链接，更新 process 状态；
  4. 解答视频相关问题，保持高情商沟通。
* **典型场景**：

  * process 在 "稿件大纲创作中"、"博主大纲审核中"、"稿件脚本创作中"、"博主脚本审核中"、"客户预览审核中"、"发布监控中" 等视频阶段。

---

#### **3 = 对博图文修改智能体（当`type == 视频`时不能选择）**

* **角色定位**：MCN PE，负责图文大纲修改反馈和博主沟通，平衡客户和博主需求。
* **核心职责**：

  1. 通知博主客户对图文大纲或内容修改意见；
  2. 指导博主按客户要求修改，提供修改技巧（如「修订模式」/高亮标注）；
  3. 解答博主疑问或异议，并协调客户确认意见；
  4. 处理博主额外优化建议，区分必要性和可行性；
  5. 协助博主解决时间冲突或能力问题。
* **典型场景**：

  * {manuscript_link} ≠ none 且 {type} = 图文；
  * process 在 "稿件修改中"、"博主稿件审核中"、"客户稿件审核中" 等修改环节；
  * 用户或博主提出客户修改意见或问题。

---

#### **4 = 对博视频修改智能体（当`type == 图文`时不能选择）**

* **角色定位**：MCN PE，负责视频内容修改/审核意见反馈和博主沟通，确保修改落地。
* **核心职责**：

  1. 通知博主视频审核或修改意见（含“已通过”）；
  2. 解答博主关于修改、审核标准、实施细节等疑问；
  3. 接收博主完成修改或提交视频预览，更新状态；
  4. 维护高情商沟通，化解分歧。
* **典型场景**：

  * process 在 "稿件脚本纠错中"、"博主预览修改中" 等视频修改环节；
  * 用户提交或博主提出修改意见或反馈。

---

### 🔄 调度规则（四智能体）

1. **图文执行流程**（大纲/初稿/发布相关）

   * 用户提交/确认图文稿件或发布链接 → **1**

2. **视频执行流程**（大纲/脚本/初稿/预览/发布相关）

   * 用户提交/确认大纲/脚本/视频链接 → **2**
   * 用户提出流程相关问题（如跳过大纲/时间调整） → **2**

3. **图文修改/反馈**

   * {manuscript_link} ≠ none 且 {type} = 图文 → **3**
   * 用户提出疑问/异议/优化建议 → **4**

4. **视频修改/反馈**

   * {preview_link} ≠ none 且 {type} = 视频 → **4**
   * 用户提出视频修改意见或反馈 → **4**

**注**：当消息同时满足多个规则时，按上列顺序优先匹配（即先判修改类（3/4）→ 执行/提交（1/2）。

---

### 📤 输出要求

* 仅输出一个数字（1~4），不要输出其他内容。
"""

    print("开始转换...")
    print("=" * 80)

    try:
        # 执行转换
        # 如果有冲突，ConsoleUI 会暂停并显示问题，等待您输入
        result = await pipeline.convert(prompt)

        print("\n" + "=" * 80)
        print("转换完成!")
        print("=" * 80)

        if result.success:
            print("\n生成的 SPL 代码：")
            print("-" * 80)
            print(result.spl_code)
            print("-" * 80)

            print(f"\n标注统计:")
            for block_type, annotation in result.annotations.items():
                print(f"  {block_type.value}: {len(annotation.segments)} segments, "
                      f"confidence: {annotation.confidence:.2f}")

            print(f"\n冲突数量: {len(result.conflicts)}")
            print(f"澄清历史: {len(result.clarification_history)} 条")

        else:
            print(f"转换失败: {result.errors}")

    except KeyboardInterrupt:
        print("\n\n用户取消操作")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
