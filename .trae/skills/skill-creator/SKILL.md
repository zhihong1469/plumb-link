# 技能创建器

> **版本**：v1.0  
> **日期**：2026-06-17  
> **类型**：生成器专用技能  
> **功能**：根据分析结果创建技能目录结构

---

## 触发条件

**触发关键词**：
- "创建技能"
- "生成技能目录"
- "创建新技能"

**输入**：
- 技能分析结果（来自 skill-analyzer）

**输出**：
- 创建结果（JSON格式）

---

## 输入格式

```json
{
  "skill_name": "skill-name",
  "category": "hardware",
  "function": "功能描述",
  "path": "skills/hardware/skill-name/",
  "description": "技能描述",
  "keywords": ["关键词1", "关键词2"],
  "platforms": ["linux", "windows"],
  "required_tools": ["tool1"]
}
```

---

## 输出格式

```json
{
  "status": "success",
  "summary": "技能创建成功",
  "skill": {
    "name": "skill-name",
    "category": "hardware",
    "path": "skills/hardware/skill-name/"
  },
  "created_files": [
    "skills/hardware/skill-name/SKILL.md",
    "skills/hardware/skill-name/scripts/src/main.py",
    "skills/hardware/skill-name/agents/openai.yaml"
  ]
}
```

---

## 创建流程

### 1. 创建目录结构

```
skills/{category}/{skill-name}/
├── SKILL.md              # 技能契约
├── scripts/              # 脚本目录
│   └── src/
│       └── main.py      # 主脚本
└── agents/               # 大模型接口
    └── openai.yaml       # 接口配置
```

### 2. 生成 SKILL.md

根据 `.trae/templates/skill/SKILL.md` 模板生成技能契约

### 3. 生成主脚本

根据技能类型生成对应的主程序

### 4. 生成 openai.yaml

根据技能信息生成大模型接口配置

---

## 文件模板

### SKILL.md 模板

```markdown
---
name: {skill-name}
version: 1.0.0
description: {description}
keywords: {keywords}
platforms: {platforms}
required_tools: {required_tools}
output_format: structured
author: "Plumb-Link Team"
license: "MIT"
---

# 技能说明

## 触发条件
- {触发关键词1}
- {触发关键词2}

## 执行步骤
1. 步骤1
2. 步骤2
3. 步骤3

## 输出格式
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | ✅ | success/partial/failure |
| summary | string | ✅ | 执行摘要 |
| evidence | array | ✅ | 输出文件列表 |
| failure_category | string | ❌ | 失败类型 |
| error_code | string | ❌ | 错误码 |

## 依赖工具
| 工具名称 | 用途 |
|---------|------|
| {工具1} | {用途1} |

## 安全注意事项
- 注意1
```

### openai.yaml 模板

```yaml
interface:
  display_name: "{显示名称}"
  short_description: "{简短描述}"
  default_prompt: |
    使用 {skill-name} 技能完成任务...

intent_keywords:
  - "{关键词1}"
  - "{关键词2}"

platforms:
  - linux
  - windows

required_tools:
  - {工具1}
```

---

## 失败处理

### 路径冲突

```json
{
  "status": "failure",
  "failure_category": "path_conflict",
  "error_code": "CRE_001",
  "summary": "技能路径已存在",
  "existing_path": "skills/hardware/gpio-config/",
  "suggestions": [
    "使用不同的技能名称",
    "先删除已存在的技能"
  ]
}
```

### 目录创建失败

```json
{
  "status": "failure",
  "failure_category": "directory_error",
  "error_code": "CRE_002",
  "summary": "目录创建失败",
  "error_details": "权限不足",
  "suggestions": [
    "检查目录权限",
    "手动创建目录"
  ]
}
```
