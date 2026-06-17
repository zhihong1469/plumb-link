---
name: {{skill_name}}
description: {{description}}
metadata:
  category: {{category}}
  version: 1.0.0
  keywords: {{keywords}}
  platforms: {{platforms}}
  tools: {{tools}}
  internal: false
---

# {{skill_title}}

## 适用场景

- 描述会触发这个 skill 的用户请求或仓库状态。
- 明确输入输出的边界条件。

## 必要输入

- 列出这个 skill 运行所需的最小输入。
- 明确哪些输入可以省略并通过自动探测补齐。

## 自动探测

- 说明这个 skill 应该优先检查什么。
- 写清显式输入、工作区线索和默认值之间的优先级。
- 探测结果会保存到 `.trae/settings.json`。

## 执行步骤

1. 按顺序描述执行流程。
2. 保持足够具体，确保执行安全。
3. 明确默认命令、模式或产物偏好。
4. 调用共享模块时使用标准导入方式。

## 失败分流

- 将常见失败映射到 `shared/failure-taxonomy.md` 中的分类。
- 说明在什么情况下应该停下来询问，而不是继续猜测。

## 平台说明

- 只保留会影响本 skill 执行的宿主平台差异。
- 利用 `shared/project_detect.py` 的 `detect_os()` 进行平台判断。

## 输出约定

- 定义预期的状态、摘要、证据和下一步动作。
- 列出这个 skill 会为 `Project Profile` 新增或更新哪些字段。
- 输出结果应便于大模型理解和后续处理。

## 交接关系

- 说明在成功、部分成功或阻塞后，应该推荐哪个下游 skill。
- 提供清晰的推荐逻辑和条件判断。

## 依赖工具

- 列出本 skill 依赖的外部工具列表。
- 工具路径通过 `shared/tool_config.py` 统一管理。

## 示例交互

```
👤 用户输入
🤖 技能响应
...
```

---

## 模板变量说明

| 变量 | 说明 | 示例 |
|------|------|------|
| `{{skill_name}}` | 技能名称（小写连字符格式） | build-linux-app |
| `{{skill_title}}` | 技能标题（中文） | Linux 应用编译 |
| `{{description}}` | 技能描述（一句话） | 编译 Linux 应用程序 |
| `{{category}}` | 技能分类 | software |
| `{{keywords}}` | 关键词列表 | ["编译", "build", "cmake"] |
| `{{platforms}}` | 支持平台 | ["windows", "linux"] |
| `{{tools}}` | 依赖工具 | ["gcc", "make", "cmake"] |
