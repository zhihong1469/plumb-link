# Plumb-Link 技能生成器

> **版本**：v1.0  
> **日期**：2026-06-17  
> **类型**：工具类技能（技能生成）  
> **参考依据**：[02_器具落地规则.md](../guide/02_器具落地规则.md)、[06_plumb-link技能生成器规则.md](../guide/06_plumb-link技能生成器规则.md)

---

## 触发条件

### 生成技能触发关键词

- "生成一个技能"
- "创建一个新技能"
- "生成技能"
- "我想实现一个XXX的技能"
- "我需要一个XXX技能"

### 删除技能触发关键词

- "删除一个技能"
- "移除一个技能"
- "删除技能"
- "我想删除XXX技能"
- "移除XXX技能"

**触发场景**：
在 plumb-link 根目录下，用户请求生成或删除技能。

---

## 功能概述

技能生成器允许用户通过自然语言请求生成或删除技能。

### 生成技能
AI 会：
1. 分析用户需求
2. 判断是否为最小单元
3. 确定技能分类和路径
4. 生成技能目录结构
5. 更新技能注册表

### 删除技能
AI 会：
1. 验证删除请求
2. 检查技能存在性
3. 检查依赖关系
4. 删除技能目录
5. 更新技能注册表

---

## 完整工作流程

### 生成技能流程

```
用户请求生成技能
    │
    ▼
读取 .trae/SKILL.md（本文档）
    │
    ▼
引用 .trae/rules/ 下的规则文件：
├── 00-skill-generation.md      # 技能生成总则
├── 01-minimal-unit.md          # 最小单元分析规则
├── 02-path-structure.md        # 路径结构规范
├── 03-metadata-std.md          # 元数据标准
└── 04-registry-update.md       # 注册表更新规则
    │
    ▼
执行 .trae/skills/ 下的生成器技能：
├── skill-analyzer/        # 技能分析器
├── skill-creator/         # 技能创建器
└── registry-updater/      # 注册表更新器
    │
    ▼
生成技能到 plumb-link/skills/{category}/{skill-name}/
    │
    ▼
返回生成结果
```

### 删除技能流程

```
用户请求删除技能
    │
    ▼
读取 .trae/SKILL.md（本文档）
    │
    ▼
引用 .trae/rules/ 下的规则文件：
├── 00-skill-generation.md      # 技能生成总则
└── 05-skill-removal.md         # 技能删除规则
    │
    ▼
验证删除请求：
├── 检查技能存在性
├── 检查依赖关系
└── 检查核心技能保护
    │
    ▼
删除技能目录：plumb-link/skills/{category}/{skill-name}/
    │
    ▼
更新注册表：agents/skill_registry.yaml
    │
    ▼
返回删除结果
```

---

## 分类体系

技能分为四大类：

| 分类 | 说明 | 示例 |
|------|------|------|
| **software** | 软件相关技能 | build-linux-app、nfs-mount |
| **hardware** | 硬件相关技能 | gpio-config、i2c-scan |
| **platform** | 平台相关技能 | freertos-config、linux-build |
| **workflow** | 工作流相关技能 | project-init、deploy-release |

---

## 输出格式

技能生成完成后，返回以下结构化信息：

| 字段 | 类型 | 说明 |
|------|------|------|
| status | string | success/partial/failure |
| summary | string | 执行摘要 |
| generated_skills | array | 生成的技能列表 |
| skill_paths | array | 技能路径列表 |
| next_steps | array | 下一步建议 |

---

## 示例对话

### 示例1：生成简单技能

```
用户：我想生成一个 GPIO 配置技能

AI 分析：
- 技能名称：gpio-config
- 分类：hardware
- 最小单元：是
- 路径：skills/hardware/gpio-config/

生成结果：
✓ 已生成技能：gpio-config
  路径：skills/hardware/gpio-config/
```

### 示例2：生成复杂技能

```
用户：我想生成一个 NFS 网络挂载开发板的技能

AI 分析：
- 最小单元：否
- 拆分方案：
  1. nfs-mount：NFS 挂载
  2. network-config：网络配置

生成结果：
✓ 已生成技能：nfs-mount
✓ 已生成技能：network-config
```

### 示例3：删除技能

```
用户：我想删除 old-skill 技能

AI 分析：
- 技能名称：old-skill
- 分类：software
- 路径：skills/software/old-skill/

检查依赖关系：
- 无其他技能依赖此技能

删除结果：
✓ 已删除技能目录：skills/software/old-skill/
✓ 已更新注册表：agents/skill_registry.yaml
```

### 示例4：删除失败（依赖冲突）

```
用户：我想删除 tool_config 技能

AI 分析：
- 技能名称：tool_config
- 路径：shared/tool_config.py

检查依赖关系：
⚠️ 检测到以下技能依赖此技能：
  - build-linux-app
  - git-commit
  - gpio-config

删除失败！请先删除依赖此技能的所有技能，或者保留此技能。
```

### 示例5：删除失败（核心技能保护）

```
用户：我想删除 build-linux-app 技能

AI 分析：
- 技能名称：build-linux-app
- 分类：software

⚠️ 此技能是 plumb-link 的核心技能，受保护无法删除。

如需修改，请使用更新版本功能。
```

---

## 安全注意事项

### 生成技能安全注意事项

1. **最小单元原则**：技能应拆分到最小单元，避免大而全
2. **分类准确性**：根据技能功能准确分类
3. **命名规范性**：使用小写字母和连字符
4. **注册表同步**：生成后必须更新 skill_registry.yaml

### 删除技能安全注意事项

1. **依赖检查**：删除前检查是否有其他技能依赖此技能
2. **核心技能保护**：核心技能受保护，无法删除
3. **完整清理**：删除技能目录和注册表记录
4. **确认删除意图**：与用户确认删除意图

---

## 参考文档

### 生成技能参考文档

- [00-skill-generation.md](rules/00-skill-generation.md) - 技能生成总则
- [01-minimal-unit.md](rules/01-minimal-unit.md) - 最小单元分析规则
- [02-path-structure.md](rules/02-path-structure.md) - 路径结构规范
- [03-metadata-std.md](rules/03-metadata-std.md) - 元数据标准
- [04-registry-update.md](rules/04-registry-update.md) - 注册表更新规则

### 删除技能参考文档

- [05-skill-removal.md](rules/05-skill-removal.md) - 技能删除规则
