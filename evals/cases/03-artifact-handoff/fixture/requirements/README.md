# 需求目录

本仓库的需求资料按作用域存放，**作用域根是 `requirements/<scope>/`**。

```
requirements/<scope>/
├── README.md     需求 README（范围、已交付、未交付、关键决定、未决问题）
├── documents/    PRD、SPEC、设计
├── issues/       issue-NNN-<slug>.md；loop-it 的检查点 .loop-state.json 也在这一层
├── notes/        实现笔记、走查件
└── records/      交付复盘
```

新建需求时取下一个顺序号建目录，并在下面的「当前顺序」表里登记。

## 当前顺序

| 序号 | 目录 | 首次纳入 |
|---|---|---|
| 01 | 01_REQ-low-stock-threshold | 2026-09-20 |
