---
name: ppt-review-workflow
description: >
  Reviewer角色的PPT审稿工作流。使用pptx-generator技能按设计系统重构PPT，
  保持内容和逻辑，优化结构、排版、配色、字体。输出修改清单。
license: MIT
metadata:
  version: "1.0"
  category: productivity
  roles:
    - reviewer
  related_skills:
    - pptx-generator
---

# PPT审稿工作流

## 问题背景

Reviewer角色配置了`pptx-generator`技能，但通过`delegate_task`分发时，子agent不会自动加载技能，只会使用基础库（python-pptx）做浅层分析，无法实现真正的视觉优化。

## 正确工作流

### Step 1: 加载技能

```
skill_view("pptx-generator")
```

阅读技能文档，了解设计系统、配色方案、字体规范。

### Step 2: 提取原PPT内容

```python
from pptx import Presentation

prs = Presentation("原文件.pptx")
for slide in prs.slides:
    for shape in slide.shapes:
        if hasattr(shape, "text"):
            # 提取文本、位置、样式
```

### Step 3: 选择设计系统

**商务深蓝主题**（推荐用于项目汇报）：
```javascript
const theme = {
  primary: "1E3A5F",      // 深蓝 - 主标题
  secondary: "475569",    // 灰蓝 - 正文
  accent: "3B82F6",       // 亮蓝 - 强调
  success: "10B981",      // 绿色 - 正向数据
  danger: "B91C1C",       // 红色 - 警示
  bg: "FFFFFF",           // 白色 - 背景
  bgDark: "0F172A"        // 深色 - 封面背景
};
```

**字体规范**：
- 中文：Microsoft YaHei（微软雅黑）
- 英文/数字：Arial

### Step 4: 用PptxGenJS重建

创建 `slides/` 目录，每页一个JS文件：

```
slides/
├── slide-01.js   # 封面
├── slide-02.js   # 内容页
├── ...
├── compile.js    # 编译脚本
└── output/
    └── 审稿优化版.pptx
```

**compile.js模板**：
```javascript
const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = 'LAYOUT_16x9';

const theme = {
  primary: "1E3A5F",
  secondary: "475569",
  accent: "3B82F6",
  success: "10B981",
  danger: "B91C1C",
  bg: "FFFFFF",
  bgDark: "0F172A"
};

for (let i = 1; i <= N; i++) {
  const num = String(i).padStart(2, '0');
  const slideModule = require(`./slide-${num}.js`);
  slideModule.createSlide(pres, theme);
}

pres.writeFile({ fileName: './output/审稿优化版.pptx' });
```

### Step 5: 执行编译

```bash
cd slides && node compile.js
```

### Step 6: 输出修改清单

列出具体修改项：
- 配色统一（X种 → Y种主题色）
- 字体规范（中文/英文）
- 布局优化（卡片、标签、流程图等）
- 文本修正（如有）

## 页面类型模板

### 封面（Cover）
- 深色背景 + 半透明装饰图形
- 主标题 + 副标题 + 日期

### 内容页（Content）
- 白色背景
- 页标题 + 左侧装饰线
- 内容区（卡片/列表/表格）
- 页脚 + 页码徽章

### 总结页（Summary）
- 行动项列表
- 优先级指示
- 结束语

## 注意事项

1. **保持内容**：不修改核心数据和结论
2. **保持逻辑**：不改变页面顺序和信息层级
3. **输出修改清单**：让用户知道改了什么
4. **MD5验证**：确认新文件与原文件不同

## 依赖

```bash
npm install -g pptxgenjs
pip install python-pptx
```

## 执行方式

不要用 `delegate_task`（会丢失技能加载），直接在当前agent执行：

1. `skill_view("pptx-generator")`
2. 提取内容
3. 创建PptxGenJS脚本
4. `node compile.js`
5. 输出修改清单