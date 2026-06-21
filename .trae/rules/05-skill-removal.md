# 技能删除规则

> **版本**：v1.0  
> **日期**：2026-06-17  
> **参考依据**：[00_道-法-器三维架构：技能开发标准原则.md](../../guide/00_道法层技能开发标准层原则.md)（四大元原则）

---

## 一、删除原则

### 1.1 核心原则

技能删除必须遵循以下原则：

| 原则 | 说明 | 约束 |
|------|------|------|
| **安全删除** | 确认删除前进行验证 | 避免误删 |
| **完整清理** | 删除技能的所有相关文件 | 避免残留 |
| **注册表同步** | 同步更新注册表 | 保持一致性 |
| **依赖检查** | 检查是否有其他技能依赖 | 避免破坏依赖关系 |

### 1.2 禁止行为

| 禁止 | 原因 | 示例 |
|------|------|------|
| **强制删除** | 不进行确认直接删除 | 删除核心技能 |
| **删除共享依赖** | 共享模块可能被其他技能使用 | 删除 shared/tool_config.py |
| **只删除目录** | 不更新注册表 | 只删除 skills/ 目录 |
| **批量删除** | 一次删除多个技能 | 影响系统稳定性 |

---

## 二、删除流程

### 2.1 六步删除法

```
步骤 1：验证删除请求
    │
    ▼
步骤 2：检查技能存在性
    │
    ▼
步骤 3：检查依赖关系
    │
    ▼
步骤 4：删除技能目录
    │
    ▼
步骤 5：更新技能注册表
    │
    ▼
步骤 6：返回删除结果
```

### 2.2 每步要求

| 步骤 | 输入 | 输出 | 关键检查 |
|------|------|------|---------|
| 1. 验证请求 | 用户请求 | 技能名称 | 是否为删除请求 |
| 2. 检查存在 | 技能名称 | 技能路径 | 技能是否存在 |
| 3. 检查依赖 | 技能信息 | 依赖列表 | 是否有其他技能依赖 |
| 4. 删除目录 | 技能路径 | 删除结果 | 目录是否成功删除 |
| 5. 更新注册表 | 技能名称 | 更新结果 | 注册表是否更新 |
| 6. 返回结果 | 删除信息 | 结构化报告 | 删除是否成功 |

---

## 三、删除验证

### 3.1 删除前检查

| 检查项 | 检查内容 | 不通过处理 |
|--------|---------|-----------|
| **请求有效性** | 用户请求是否为删除技能 | 返回提示 |
| **技能存在性** | 技能是否存在于 skills/ 目录 | 返回错误 |
| **注册表一致性** | 技能是否在注册表中 | 返回警告 |
| **依赖关系** | 是否有其他技能依赖此技能 | 返回警告 |
| **核心技能保护** | 是否为核心技能（如 build-linux-app） | 返回错误 |

### 3.2 删除后验证

| 检查项 | 检查内容 | 失败处理 |
|--------|---------|--------|
| **目录删除** | 技能目录是否已删除 | 手动删除 |
| **注册表更新** | 注册表是否已更新 | 手动更新 |
| **残留文件** | 是否有残留文件 | 清理残留 |

---

## 四、错误处理

### 4.1 常见错误

| 错误类型 | 原因 | 处理方式 |
|---------|------|---------|
| **技能不存在** | 用户指定的技能不存在 | 返回错误信息 |
| **核心技能保护** | 尝试删除核心技能 | 返回错误信息 |
| **依赖冲突** | 其他技能依赖此技能 | 返回依赖列表 |
| **权限不足** | 没有删除权限 | 返回错误信息 |

### 4.2 错误响应格式

```json
{
  "status": "failure",
  "failure_category": "skill_not_found",
  "error_code": "REM_001",
  "summary": "技能不存在",
  "skill_name": "unknown-skill",
  "suggestions": [
    "检查技能名称是否正确",
    "使用 --list 查看可用技能"
  ]
}
```

### 4.3 依赖冲突响应格式

```json
{
  "status": "failure",
  "failure_category": "dependency_conflict",
  "error_code": "REM_002",
  "summary": "技能被其他技能依赖",
  "skill_name": "tool_config",
  "dependent_skills": [
    "build-linux-app",
    "git-commit",
    "gpio-config"
  ],
  "suggestions": [
    "先删除依赖此技能的所有技能",
    "或者保留此技能"
  ]
}
```

### 4.4 核心技能保护响应格式

```json
{
  "status": "failure",
  "failure_category": "core_skill_protection",
  "error_code": "REM_003",
  "summary": "核心技能受保护，无法删除",
  "skill_name": "build-linux-app",
  "reason": "此技能是 plumb-link 的核心技能",
  "suggestions": [
    "核心技能不能删除",
    "如需修改，请使用更新版本功能"
  ]
}
```

---

## 五、删除输出

### 5.1 成功输出

```json
{
  "status": "success",
  "summary": "技能删除成功",
  "deleted_skill": {
    "name": "old-skill",
    "category": "software",
    "version": "1.0.0"
  },
  "deleted_path": "skills/software/old-skill/",
  "registry_updated": true,
  "registry_location": "agents/skill_registry.yaml"
}
```

### 5.2 带警告的输出

```json
{
  "status": "success",
  "summary": "技能删除成功（带警告）",
  "deleted_skill": {
    "name": "old-skill",
    "category": "software",
    "version": "1.0.0"
  },
  "deleted_path": "skills/software/old-skill/",
  "warnings": [
    "注册表中未找到此技能记录",
    "可能已被手动删除"
  ],
  "registry_updated": false
}
```

---

## 六、核心技能保护

### 6.1 核心技能列表

| 技能名称 | 分类 | 保护原因 |
|---------|------|---------|
| build-linux-app | software | 核心编译技能 |
| git-commit | software | 核心版本控制技能 |
| project-init | workflow | 核心项目初始化技能 |

### 6.2 保护机制

1. **检查核心技能列表**：删除前检查是否为核心技能
2. **返回保护信息**：返回错误信息和保护原因
3. **提供替代方案**：建议使用更新版本功能

---

## 七、依赖检查

### 7.1 依赖检查流程

```
检查技能的 shared_deps
    │
    ▼
检查是否有其他技能依赖此技能
    │
    ├─ 无依赖 → 允许删除
    │
    └─ 有依赖 → 返回依赖列表
```

### 7.2 依赖检查示例

```python
# 检查技能依赖
def check_dependencies(skill_name: str, registry: dict) -> list:
    """检查是否有其他技能依赖此技能"""
    dependent_skills = []
    for skill in registry.get("skills", []):
        shared_deps = skill.get("shared_deps", [])
        if skill_name in shared_deps:
            dependent_skills.append(skill["name"])
    return dependent_skills
```

---

## 八、最佳实践

### 8.1 删除前

1. **确认技能名称**：确保技能名称正确
2. **检查依赖关系**：确认没有其他技能依赖
3. **备份技能**：如需要，先备份技能
4. **确认删除意图**：与用户确认删除意图

### 8.2 删除中

1. **完整删除**：删除技能目录下的所有文件
2. **更新注册表**：从注册表中删除技能记录
3. **检查残留**：确保没有残留文件
4. **记录日志**：记录删除操作

### 8.3 删除后

1. **验证删除**：确认技能目录已删除
2. **验证注册表**：确认注册表已更新
3. **返回详细信息**：提供完整删除报告
4. **给出建议**：提供下一步操作建议

---

## 九、与安装脚本集成

### 9.1 安装脚本命令

```bash
# 删除单个技能
python scripts/install.py /path/to/project --remove skill-name

# 删除多个技能
python scripts/install.py /path/to/project --remove skill1 skill2

# 卸载全部技能
python scripts/install.py /path/to/project --uninstall
```

### 9.2 生成器与安装脚本的区别

| 功能 | 生成器 | 安装脚本 |
|------|--------|---------|
| **删除位置** | 从 plumb-link 仓库删除 | 从目标项目删除 |
| **注册表** | 更新 skill_registry.yaml | 更新 .em_skill_meta.json |
| **技能目录** | 删除 skills/{category}/{skill}/ | 删除 .claude/skills/{skill}/ |
| **使用场景** | 开发阶段删除技能 | 生产阶段卸载技能 |

---

## 十、示例交互

### 10.1 正常删除

```
👤 删除 old-skill 技能
🤖 正在验证删除请求...

验证结果：
- 技能名称：old-skill
- 分类：software
- 版本：1.0.0
- 路径：skills/software/old-skill/

检查依赖关系：
- 无其他技能依赖此技能

开始删除...

✓ 已删除技能目录：skills/software/old-skill/
✓ 已更新注册表：agents/skill_registry.yaml

删除完成！
```

### 10.2 依赖冲突

```
👤 删除 tool_config 技能
🤖 正在验证删除请求...

验证结果：
- 技能名称：tool_config
- 分类：shared
- 路径：shared/tool_config.py

检查依赖关系：
⚠️ 检测到以下技能依赖此技能：
  - build-linux-app
  - git-commit
  - gpio-config

删除失败！请先删除依赖此技能的所有技能，或者保留此技能。
```

### 10.3 核心技能保护

```
👤 删除 build-linux-app 技能
🤖 正在验证删除请求...

验证结果：
- 技能名称：build-linux-app
- 分类：software
- 版本：1.0.0

⚠️ 此技能是 plumb-link 的核心技能，受保护无法删除。

如需修改，请使用更新版本功能。
```