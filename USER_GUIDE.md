# Plumb-Link 用户操作规范

> **版本**：v1.0  
> **日期**：2026-06-17  
> **适用对象**：技能开发者、架构设计师

---

## 一、如何创建新技能

### 1.1 触发方式

**自然语言触发**（推荐）：
```
👤 我想创建一个 [技能功能描述] 的技能
👤 生成一个 [技能功能描述] 技能
👤 帮我实现一个 [技能功能描述] 的技能
```

**示例**：
```
👤 我想创建一个 GPIO 配置技能
👤 生成一个 NFS 网络挂载技能
👤 帮我实现一个 Linux 内核编译技能
```

### 1.2 技能命名规范

| 规则 | 要求 | 示例 | 反例 |
|------|------|------|------|
| **小写字母** | 全部使用小写 | `gpio-config` | `GPIO-Config` |
| **连字符分隔** | 使用 `-` 分隔单词 | `nfs-mount` | `nfs_mount` |
| **不超过20字符** | 名称简洁 | `linux-build` | `linux-kernel-build-script` |
| **英文命名** | 使用英文单词 | `i2c-scan` | `i2c扫描` |
| **无空格** | 不使用空格 | `spi-debug` | `spi debug` |

### 1.3 技能分类

| 分类 | 说明 | 示例 |
|------|------|------|
| **software** | 软件相关技能 | build-linux-app、nfs-mount |
| **hardware** | 硬件相关技能 | gpio-config、i2c-scan、spi-debug |
| **platform** | 平台相关技能 | linux-build、freertos-config |
| **workflow** | 工作流技能 | project-init、deploy-release |

---

## 二、模板文件用途说明

### 2.1 `.trae/templates/` 目录

**用途**：给 AI 技能生成器使用的模板，用于自动生成技能文件。

| 文件 | 用途 | 使用对象 |
|------|------|----------|
| `SKILL.md` | 技能定义规范模板 | AI（生成技能时使用） |
| `CHECKLIST.md` | 技能开发检查清单 | AI + 开发者（验证技能） |
| `SCENARIOS.md` | 场景覆盖定义模板 | AI（生成场景文档） |

**工作原理**：
```
用户请求 → AI读取模板 → 填充变量 → 生成技能文件
```

**模板变量**：
```
{{skill_name}}     - 技能名称（小写连字符格式）
{{skill_title}}    - 技能标题（中文）
{{description}}    - 技能描述（一句话）
{{category}}       - 技能分类
{{keywords}}       - 关键词列表
{{platforms}}      - 支持平台
{{tools}}          - 依赖工具
```

### 2.2 `templates/code/` 目录

**用途**：给 AI 生成代码时使用的输出模板。

| 模板 | 用途 | 示例 |
|------|------|------|
| C代码模板 | 生成C语言代码 | main.c |
| Python代码模板 | 生成Python脚本 | main.py |
| Shell脚本模板 | 生成Shell脚本 | build.sh |
| Makefile模板 | 生成Makefile | Makefile |
| CMakeLists.txt模板 | 生成CMake配置 | CMakeLists.txt |

### 2.3 `templates/report/` 目录

**用途**：给 AI 生成报告时使用的输出模板。

| 模板 | 用途 | 示例 |
|------|------|------|
| 代码审查报告 | 生成代码审查报告 | code-review.md |
| 测试报告 | 生成测试报告 | test-report.md |
| 性能分析报告 | 生成性能分析报告 | performance.md |
| 安全审计报告 | 生成安全审计报告 | security-audit.md |

---

## 三、技能生成流程

### 3.1 完整流程

```
用户请求创建技能
    │
    ▼
步骤1：AI读取 .trae/SKILL.md（生成器入口）
    │
    ▼
步骤2：分析需求 → 判断最小单元 → 确定分类和路径
    │
    ▼
步骤3：检查技能是否已存在（防重复）
    │
    ├─ 已存在 → 返回冲突提示，建议使用不同名称或更新现有技能
    │
    └─ 不存在 → 继续生成
    │
    ▼
步骤4：生成技能目录结构
    │
    └── skills/{category}/{skill-name}/
        ├── SKILL.md
        ├── scripts/src/main.py
        └── agents/openai.yaml
    │
    ▼
步骤5：更新技能注册表（agents/skill_registry.yaml）
    │
    ▼
步骤6：返回生成结果
```

### 3.2 最小单元分析

AI 会自动分析技能需求，判断是否需要拆分：

**需要拆分的情况**：
- 多步骤流程（如"编译并烧录"应拆分为两个技能）
- 涉及多个接口（如"I2C和SPI配置"应拆分）
- 涉及多个平台（如"Linux和RTOS配置"应拆分）
- 配置和执行分离（如"配置并运行"应拆分）

**可保留的情况**：
- 单一操作（如"GPIO配置"）
- 紧密关联的步骤（如"make编译"）
- 原子操作（如"I2C扫描"）

### 3.3 重复检查机制

**检查内容**：
1. **技能名称冲突**：检查 `agents/skill_registry.yaml` 中是否已存在同名技能
2. **目录路径冲突**：检查 `skills/{category}/` 下是否已存在同名目录

**冲突处理**：
```json
{
  "status": "failure",
  "failure_category": "skill_conflict",
  "error_code": "REG_002",
  "summary": "技能已存在",
  "existing_skill": {
    "name": "gpio-config",
    "category": "hardware",
    "version": "1.0.0"
  },
  "suggestions": [
    "使用不同的技能名称",
    "更新现有技能版本"
  ]
}
```

---

## 四、用户操作示例

### 4.1 创建简单技能

```
👤 我想创建一个 GPIO 配置技能

🤖 正在分析技能需求...

分析结果：
- 技能名称：gpio-config
- 分类：hardware
- 最小单元：是
- 路径：skills/hardware/gpio-config/

开始生成...

✓ 已生成技能：gpio-config
  路径：skills/hardware/gpio-config/
✓ 已更新注册表：agents/skill_registry.yaml

下一步建议：
1. 完善 scripts/src/main.py 实现逻辑
2. 添加测试用例到 testcases/
3. 补充 agents/openai.yaml 配置
```

### 4.2 创建复杂技能（需要拆分）

```
👤 我想创建一个 NFS 网络挂载开发板的技能

🤖 正在分析技能需求...

分析结果：
- 是否为最小单元：否
- 拆分方案：
  1. nfs-mount（NFS挂载）→ software
  2. network-config（网络配置）→ software
  3. board-detect（开发板检测）→ platform

开始生成...

✓ 已生成技能：nfs-mount
  路径：skills/software/nfs-mount/
✓ 已生成技能：network-config
  路径：skills/software/network-config/
✓ 已生成技能：board-detect
  路径：skills/platform/board-detect/

✓ 已更新注册表：agents/skill_registry.yaml

下一步建议：
1. 完善各技能脚本实现
2. 编写测试用例
3. 添加参考文档
```

### 4.3 处理冲突

```
👤 我想创建一个 GPIO 配置技能

🤖 正在分析技能需求...

⚠️ 检测到技能已存在：

技能名称：gpio-config
分类：hardware
当前版本：1.0.0

请选择操作：
1. 使用不同名称重新生成
2. 更新现有技能版本
3. 取消操作

👤 2

🤖 正在更新技能：gpio-config...

✓ 技能已更新：gpio-config（版本：1.0.1）
✓ 已更新注册表：agents/skill_registry.yaml
```

---

## 五、如何删除技能

### 5.1 删除技能的触发方式

**自然语言触发**（推荐）：
```
👤 我想删除一个 [技能名称] 技能
👤 移除一个 [技能名称] 技能
👤 删除技能 [技能名称]
```

**示例**：
```
👤 我想删除 old-skill 技能
👤 移除 gpio-config 技能
```

### 5.2 删除技能的流程

```
用户请求删除技能
    │
    ▼
验证删除请求
    │
    ▼
检查技能存在性
    │
    ▼
检查依赖关系
    │
    ├─ 有依赖 → 返回依赖列表，提示用户
    │
    └─ 无依赖 → 继续
    │
    ▼
检查核心技能保护
    │
    ├─ 核心技能 → 返回保护信息，拒绝删除
    │
    └─ 非核心技能 → 继续
    │
    ▼
删除技能目录
    │
    ▼
更新技能注册表
    │
    ▼
返回删除结果
```

### 5.3 删除安全机制

| 安全机制 | 说明 | 示例 |
|---------|------|------|
| **依赖检查** | 检查是否有其他技能依赖此技能 | tool_config 被 build-linux-app 依赖 |
| **核心技能保护** | 核心技能受保护无法删除 | build-linux-app、git-commit |
| **完整清理** | 同时删除技能目录和注册表记录 | 删除 skills/ 和 skill_registry.yaml |
| **确认删除意图** | 与用户确认删除意图 | 提示用户确认 |

### 5.4 删除示例

**正常删除**：
```
👤 我想删除 old-skill 技能
🤖 正在验证删除请求...

验证结果：
- 技能名称：old-skill
- 分类：software
- 路径：skills/software/old-skill/

检查依赖关系：
- 无其他技能依赖此技能

开始删除...

✓ 已删除技能目录：skills/software/old-skill/
✓ 已更新注册表：agents/skill_registry.yaml

删除完成！
```

**依赖冲突**：
```
👤 我想删除 tool_config 技能
🤖 正在验证删除请求...

验证结果：
- 技能名称：tool_config
- 路径：shared/tool_config.py

检查依赖关系：
⚠️ 检测到以下技能依赖此技能：
  - build-linux-app
  - git-commit
  - gpio-config

删除失败！请先删除依赖此技能的所有技能，或者保留此技能。
```

**核心技能保护**：
```
👤 我想删除 build-linux-app 技能
🤖 正在验证删除请求...

验证结果：
- 技能名称：build-linux-app
- 分类：software

⚠️ 此技能是 plumb-link 的核心技能，受保护无法删除。

如需修改，请使用更新版本功能。
```

---

## 六、技能开发后续步骤

### 6.1 生成后需要做的事情

| 步骤 | 操作 | 说明 |
|------|------|------|
| 1 | 完善脚本实现 | 编辑 `scripts/src/main.py` |
| 2 | 添加大模型接口 | 创建 `agents/openai.yaml` |
| 3 | 编写测试用例 | 创建 `testcases/test_*.py` |
| 4 | 验证技能合规 | 运行 `python framework/skill_lint.py` |
| 5 | 测试技能功能 | 运行 `python framework/skill_test.py` |

### 6.2 技能合规检查

```bash
# 检查单个技能
python framework/skill_lint.py skills/hardware/gpio-config/

# 检查所有技能
python framework/skill_lint.py --all
```

### 6.3 技能测试

```bash
# 运行单个技能测试
python framework/skill_test.py skills/hardware/gpio-config/

# 运行所有技能测试
python framework/skill_test.py --all
```

---

## 七、技能安装与使用

### 7.1 安装技能到项目

```bash
# 安装到目标项目
python scripts/install.py /path/to/project

# 按需安装特定技能
python scripts/install.py /path/to/project --skills gpio-config i2c-scan

# 安装分类下的所有技能
python scripts/install.py /path/to/project --skills hardware/*
```

### 7.2 使用技能

**方式一：自然语言触发**
```
👤 帮我配置 GPIO 引脚
🤖 使用 gpio-config 技能，正在配置...
```

**方式二：命令调用**
```bash
# 在项目目录下
python .trae/skills/shared/env_detect.py . --format llm
```

---

## 八、常见问题

### Q1：模板文件是给AI用还是给用户用的？

**A**：`.trae/templates/` 目录下的模板是给 AI 技能生成器使用的，用于自动生成技能文件。用户不需要直接编辑这些模板，只需要通过自然语言描述需求即可。

### Q2：如何确保不会重复生成技能？

**A**：技能生成器会自动检查：
1. `agents/skill_registry.yaml` 中是否已存在同名技能
2. `skills/{category}/` 下是否已存在同名目录

如果存在冲突，会提示用户选择操作。

### Q3：技能名称可以修改吗？

**A**：可以，但需要同时更新：
1. 技能目录名称
2. `SKILL.md` 中的 `name` 字段
3. `agents/skill_registry.yaml` 中的对应记录

### Q5：如何删除一个技能？

**A**：有两种方式：

**方式一：自然语言删除（推荐）**
```
👤 我想删除 old-skill 技能
🤖 正在验证删除请求...
🤖 ✓ 已删除技能目录：skills/software/old-skill/
🤖 ✓ 已更新注册表：agents/skill_registry.yaml
```

**方式二：使用安装脚本删除**
```bash
# 删除单个技能
python scripts/install.py /path/to/project --remove gpio-config

# 删除多个技能
python scripts/install.py /path/to/project --remove gpio-config i2c-scan

# 卸载全部技能
python scripts/install.py /path/to/project --uninstall
```

**方式三：手动删除**
1. 删除技能目录：`rm -rf skills/{category}/{skill-name}/`
2. 更新注册表：从 `agents/skill_registry.yaml` 中删除对应条目

> **注意**：
> - 删除已安装到其他项目的技能时，需要在目标项目中使用 `--remove` 命令进行卸载
> - 删除前会检查依赖关系，如果有其他技能依赖此技能，会提示用户
> - 核心技能（如 build-linux-app）受保护无法删除

---

## 八、最佳实践

### 8.1 技能设计原则

1. **单一职责**：每个技能只做一件事
2. **最小单元**：尽量拆分成最小可执行单元
3. **清晰边界**：明确输入输出
4. **可复用性**：设计时考虑复用场景

### 8.2 命名最佳实践

- 使用描述性名称（如 `i2c-scan` 而非 `i2c`）
- 遵循分类规范（software/hardware/platform/workflow）
- 保持名称简洁（不超过20字符）

### 8.3 协作最佳实践

- 生成技能后及时更新注册表
- 编写测试用例确保质量
- 使用合规检查工具验证技能规范
- 文档化技能的使用场景和边界

---

**版本历史**：
- v1.0（2026-06-17）：初始版本
