# git-commit 技能配置说明

## 配置文件位置

```
skills/software/git-commit/config.json
```

---

## 分支管理工作流

### 工作流概述

支持完整的 Git 分支管理工作流：

```
1. 从主流程（main/release/*）拉取最新代码
   ↓
2. 创建功能分支（feature/v1_6ull/add-audio-support）
   ↓
3. 本地提交 n 次
   ↓
4. 合并到主流（release/v1）
   ↓
5. 推送到远程
   ↓
6. 可选删除功能分支
```

---

## 命令行参数

### 分支管理命令

| 参数 | 说明 | 示例 |
|------|------|------|
| `--create-branch NAME` | 创建新分支 | `--create-branch feature/v1_6ull/add-audio-support` |
| `--from-branch BRANCH` | 从指定分支创建 | `--from-branch release/v1` |
| `--switch-branch NAME` | 切换分支 | `--switch-branch main` |
| `--pull` | 拉取最新代码 | `--pull` |
| `--merge-to BRANCH` | 合并到指定分支 | `--merge-to release/v1` |
| `--delete-branch NAME` | 删除分支 | `--delete-branch feature/v1_6ull/add-audio-support` |
| `--force-delete` | 强制删除分支 | `--delete-branch old-feature --force-delete` |
| `--set-upstream` | 推送时设置上游分支 | `--create-branch feature/new --set-upstream` |

### 工作流命令

| 参数 | 说明 | 示例 |
|------|------|------|
| `--workflow feature` | 创建功能分支工作流 | `--workflow feature --feature-name v1_6ull/add-audio-support` |
| `--workflow merge` | 合并工作流 | `--workflow merge --target-release release/v1 --delete-after-merge` |
| `--workflow complete` | 显示完整工作流步骤 | `--workflow complete` |
| `--feature-name NAME` | 功能分支名称 | `--feature-name v1_6ull/add-audio-support` |
| `--target-release BRANCH` | 目标发布分支 | `--target-release release/v1` |
| `--delete-after-merge` | 合并后删除源分支 | `--delete-after-merge` |

---

## 配置项说明

### 分支工作流配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `branch_workflow.main_branches` | array | ["main", "release/*"] | 主分支列表 |
| `branch_workflow.feature_branch_prefix` | string | "feature/" | 功能分支前缀 |
| `branch_workflow.bugfix_branch_prefix` | string | "bugfix/" | 修复分支前缀 |
| `branch_workflow.hotfix_branch_prefix` | string | "hotfix/" | 紧急修复分支前缀 |
| `branch_workflow.auto_create_feature` | boolean | true | 自动创建功能分支 |
| `branch_workflow.auto_merge_to_main` | boolean | false | 自动合并到主分支 |
| `branch_workflow.auto_delete_after_merge` | boolean | false | 合并后自动删除源分支 |
| `branch_workflow.merge_strategy` | string | "merge" | 合并策略（merge/squash） |
| `branch_workflow.require_pull_before_merge` | boolean | true | 合并前要求拉取最新代码 |
| `branch_workflow.confirm_before_delete` | boolean | true | 删除分支前确认 |

### 分支创建配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `branch_creation.auto_create` | boolean | true | 自动创建不存在的分支 |
| `branch_creation.create_if_not_exists` | boolean | true | 分支不存在时创建 |
| `branch_creation.from_main_branch` | boolean | true | 从主分支创建新分支 |
| `branch_creation.pull_before_create` | boolean | true | 创建前拉取最新代码 |

### 合并配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `merge_config.target_branches` | array | ["main", "release/*"] | 可合并的目标分支 |
| `merge_config.require_clean_working_tree` | boolean | true | 合并前要求工作区干净 |
| `merge_config.squash_merge` | boolean | false | 使用 squash 合并 |
| `merge_config.delete_source_after_merge` | boolean | false | 合并后删除源分支 |

---

## 使用示例

### 示例1：创建功能分支

```bash
# 从 release/v1 创建功能分支
python git_commit.py --workflow feature --feature-name v1_6ull/add-audio-support --from-branch release/v1

# 输出：
🔄 执行工作流: feature
   功能分支: feature/v1_6ull/add-audio-support
   从分支: release/v1
   
   步骤 1: 拉取最新代码
   ✓ 已拉取 release/v1 最新代码
   
   步骤 2: 创建功能分支
   ✓ 已创建分支: feature/v1_6ull/add-audio-support
   
✅ 功能分支工作流完成
   当前分支: feature/v1_6ull/add-audio-support
   下一步: 开发功能并提交代码
```

### 示例2：本地提交多次

```bash
# 在功能分支上提交代码
python git_commit.py --message "feat(audio): add audio driver support"
python git_commit.py --message "feat(audio): add audio test cases"
python git_commit.py --message "docs(audio): update audio module docs"
```

### 示例3：合并到主流并删除功能分支

```bash
# 合并到 release/v1 并删除功能分支
python git_commit.py --workflow merge --target-release release/v1 --delete-after-merge

# 输出：
🔄 执行工作流: merge
   源分支: feature/v1_6ull/add-audio-support
   目标分支: release/v1
   
   步骤 1: 拉取目标分支最新代码
   ✓ 已拉取 release/v1 最新代码
   
   步骤 2: 合并分支
   ✓ 已合并 feature/v1_6ull/add-audio-support 到 release/v1
   
   步骤 3: 推送合并结果
   ✓ 已推送 release/v1 到远程
   
   步骤 4: 删除源分支
   ✓ 已删除分支: feature/v1_6ull/add-audio-support
   
✅ 合并工作流完成
```

### 示例4：手动控制分支

```bash
# 1. 拉取最新代码
python git_commit.py --pull

# 2. 创建分支
python git_commit.py --create-branch feature/new-feature --from-branch main

# 3. 切换分支
python git_commit.py --switch-branch feature/new-feature

# 4. 提交代码
python git_commit.py --message "feat: add new feature"

# 5. 合并到目标分支
python git_commit.py --merge-to release/v1 --delete-after-merge

# 6. 删除分支
python git_commit.py --delete-branch feature/new-feature --force-delete
```

---

## 分支命名规范

### 功能分支

格式：`feature/<version>/<feature-name>`

示例：
- `feature/v1_6ull/add-audio-support`
- `feature/v2_rk3562/add-video-decoder`
- `feature/common/add-logging-module`

### 修复分支

格式：`bugfix/<version>/<bug-name>`

示例：
- `bugfix/v1_6ull/fix-audio-crash`
- `bugfix/v2_rk3562/fix-boot-issue`

### 紧急修复分支

格式：`hotfix/<version>/<issue-name>`

示例：
- `hotfix/v1_6ull/fix-critical-boot-failure`

---

## 安全机制

### 分支保护

| 机制 | 说明 |
|------|------|
| 主分支保护 | main、master、release/* 受保护，不允许直接提交 |
| 删除确认 | 删除分支前需要确认（可配置） |
| 合前检查 | 合并前检查工作区是否干净 |
| 拉取检查 | 合并前拉取目标分支最新代码 |

### 推送保护

| 机制 | 说明 |
|------|------|
| 上游分支设置 | 新分支推送时可设置上游分支 |
| 推送确认 | 推送前可配置确认机制 |

---

## 常见问题

### Q1：如何创建功能分支？

**A**：
```bash
# 方式一：使用工作流
python git_commit.py --workflow feature --feature-name v1_6ull/add-audio-support

# 方式二：手动创建
python git_commit.py --create-branch feature/v1_6ull/add-audio-support --from-branch release/v1
```

### Q2：如何合并分支？

**A**：
```bash
# 方式一：使用工作流
python git_commit.py --workflow merge --target-release release/v1 --delete-after-merge

# 方式二：手动合并
python git_commit.py --merge-to release/v1
```

### Q3：如何删除分支？

**A**：
```bash
# 删除分支（需要确认）
python git_commit.py --delete-branch feature/old-feature

# 强制删除
python git_commit.py --delete-branch feature/old-feature --force-delete
```

### Q4：如何拉取最新代码？

**A**：
```bash
python git_commit.py --pull
```

### Q5：如何推送新分支到远程？

**A**：
```bash
# 创建分支并推送
python git_commit.py --create-branch feature/new --set-upstream
```

---

## 配置示例

### 开发环境配置

```json
{
  "branch_workflow": {
    "auto_create_feature": true,
    "auto_merge_to_main": false,
    "auto_delete_after_merge": false,
    "confirm_before_delete": true
  },
  "branch_creation": {
    "pull_before_create": true,
    "from_main_branch": true
  },
  "merge_config": {
    "require_clean_working_tree": true,
    "delete_source_after_merge": false
  }
}
```

### 生产环境配置

```json
{
  "branch_workflow": {
    "auto_create_feature": true,
    "auto_merge_to_main": false,
    "auto_delete_after_merge": true,
    "confirm_before_delete": true,
    "require_pull_before_merge": true
  },
  "branch_creation": {
    "pull_before_create": true,
    "from_main_branch": true
  },
  "merge_config": {
    "require_clean_working_tree": true,
    "delete_source_after_merge": true
  },
  "protected_branches": ["main", "master", "release/*"]
}
```

---

## 安全配置

### 安全开关

为确保安全，此技能默认处于禁用状态，必须由用户手动激活。

```json
{
  "security": {
    "enabled": false,
    "require_user_activation": true,
    "activation_required_message": "此技能需要用户手动激活",
    "auto_disable_after_hours": 0,
    "allowed_operations": ["commit", "branch_create", "branch_switch", "pull", "merge", "push", "delete_branch"],
    "blocked_operations": []
  }
}
```

### 安全配置项

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `security.enabled` | boolean | false | **必须手动设置为 true 才能启用技能** |
| `security.require_user_activation` | boolean | true | 是否要求用户手动激活 |
| `security.activation_required_message` | string | - | 未激活时显示的提示信息 |
| `security.auto_disable_after_hours` | int | 0 | 自动禁用时间（0=永不自动禁用） |
| `security.allowed_operations` | array | ["commit", "branch_create", "branch_switch", "pull", "merge", "push", "delete_branch"] | 允许的操作列表 |
| `security.blocked_operations` | array | [] | 禁止的操作列表 |

### 激活步骤

1. **打开配置文件**：`skills/software/git-commit/config.json`
2. **找到安全配置段**：
   ```json
   "security": {
     "enabled": false,
     ...
   }
   ```
3. **设置 enabled 为 true**：
   ```json
   "security": {
     "enabled": true,
     ...
   }
   ```
4. **保存文件**

### 安全机制说明

| 机制 | 说明 |
|------|------|
| **手动激活** | 技能默认禁用，必须用户手动开启 |
| **大模型保护** | 大模型无法自动修改配置文件 |
| **操作白名单** | 可配置允许/禁止的操作 |
| **自动禁用** | 可配置超时自动禁用（默认关闭） |

### 安全警告

当技能未激活时，运行会显示：

```
🔒 ===============================================
🔒 安全警告：此技能需要用户手动激活
🔒 ===============================================

❌ 此技能需要用户手动激活。请查看 CONFIG.md 配置文件并设置 security.enabled = true

📋 请按照以下步骤激活：
   1. 查看配置文件: skills/software/git-commit/config.json
   2. 将 security.enabled 设置为 true
   3. 确认所有配置项符合您的需求

🔒 安全说明：
   - 此技能涉及代码提交和分支管理操作
   - 必须由用户手动确认后才能使用
   - 大模型无法自动修改此开关
🔒 ===============================================
```

---

## 技能激活状态

### 当前状态

| 状态 | 值 |
|------|------|
| 是否启用 | ❌ 未启用（默认） |
| 是否需要激活 | ✅ 需要 |
| 配置文件路径 | `skills/software/git-commit/config.json` |

### 启用后状态

| 状态 | 值 |
|------|------|
| 是否启用 | ✅ 已启用 |
| 可执行操作 | commit, branch_create, branch_switch, pull, merge, push, delete_branch |