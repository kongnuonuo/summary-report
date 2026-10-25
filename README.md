# summary-report

把一次多任务的工作（排障 / 修复 / 验证 / 调研）沉淀为**固定结构的 HTML 复盘报告**。
给支持 skill 的 AI 助手使用（WorkBuddy / Claude Code 等）。

## 它解决的问题

不是"怎么排版"，而是**怎么让总结诚实**：

- 区分「已闭环 / 部分闭环 / 未闭环」
- 区分「实测 / 推断 / 假设」
- 把**反证**和正证放在同等位置

## 强制章节（缺一节即不合格）

| 章 | 标题 | 必须回答 |
|---|---|---|
| 1 | 结论 | 每件事的真实原因、状态档次 |
| 2 | 验收判据 | 用什么标准判定"修好了"，逐条给实测值 |
| 3…N | 具体项目 | 现象分流 → 证据 → 处置 → 结果 |
| N+1 | 优化项 | O1…On，三段式，含反证 |
| N+2 | 已知缺口 | 没做完的、没验证的、仍是嫌疑的 |
| N+3 | 文件与复现 | 产物清单 + 可粘贴命令 + 还原方法 |
| N+4 | 依赖与知识清单 | 库/技术 + 读者需先掌握的基础知识点 |

另含**按类型追加的必选节「它是怎么工作的」**：产出是能跑的模型（电路仿真 / 控制环 /
算法 / 状态机）时，必须多一节讲清"它凭什么能工作"——六步：能量/信号链 → 带探针名的框图 →
3–5 步机理推导 → 采样清单 → 框图↔实测对照 → 模型≠实物。

## 内容

```
SKILL.md                      规范正文
assets/report-template.html   版式骨架（CSS 变量 / KPI / 公式块 / .pass/.fail）
scripts/add_toc.py            注入左侧可折叠目录（幂等）
scripts/check_svg.py          内联 SVG 自检：文字越界 / 图形越界 / 文字重叠
references/section-guide.md   每章写作细则与正反例
```

## 用法

1. 把整个目录放进 skills 目录（如 `~/.workbuddy/skills/summary-report/`）
2. 让助手加载 `summary-report` skill
3. 复制 `assets/report-template.html` 作骨架，按强制章节写
4. 注入目录并过闸门：

```bash
python scripts/add_toc.py <报告.html>
python scripts/check_svg.py <报告.html>     # 期望 problems: 0
```

三项质量闸门：`check_svg.py` 的 `problems: 0`、标签开闭逐项配对、
无头 Chrome 展开态与折叠态各截一张图目视。

## 环境

纯 Python 标准库 + 无头 Chrome，无第三方依赖；报告与图全部手写内联 SVG，单文件离线可看。
