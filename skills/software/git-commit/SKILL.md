---
name: git-commit
version: 1.0.0
description: Git 代码提交，支持自动添加文件、生成提交信息和推送到远程仓库
keywords: ["git", "commit", "提交", "push", "代码", "版本控制"]
platforms: ["linux", "windows", "macos"]
required_tools: ["git"]
optional_tools: ["git-lfs"]
output_format: structured
author: "Plumb-Link Team"
license: "MIT"
---

# 技能说明

## 触发条件
- 用户提到"git commit"、"提交代码"、"推送"、"commit"等关键词
- 当前目录是 Git 仓库
- 需要提交代码变更

## 执行步骤
1. 检测 Git 环境和仓库状态
2. 检查当前分支信息
3. 获取变更文件列表
4. 根据参数添加文件（默认添加所有变更）
5. 生成提交信息
6. 执行 git commit
7. 可选：推送到远程仓库
8. 返回结构化结果

## 输出格式
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | ✅ | success/partial/failure |
| summary | string | ✅ | 执行摘要 |
| evidence | array | ✅ | 输出文件列表和命令信息 |
| failure_category | string | ❌ | 失败类型（仅失败时） |
| error_code | string | ❌ | 错误码（仅失败时） |

## 支持的命令行参数
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| --message | str | None | 提交信息 |
| --message-file | str | None | 提交信息文件路径 |
| --add | str | all | 添加文件模式 (all/modified/none) |
| --files | str | None | 指定提交的文件列表 |
| --amend | flag | False | 修改上次提交 |
| --push | flag | False | 提交后推送到远程 |
| --branch | str | None | 指定分支 |
| --remote | str | origin | 远程仓库名称 |
| --sign | flag | False | GPG 签名提交 |
| --dry-run | flag | False | 模拟执行，不实际提交 |
| --json | flag | False | 输出 JSON 格式结果 |

## 依赖工具
| 工具名称 | 用途 | 检测方法 |
|---------|------|---------|
| git | 版本控制 | git --version |
| git-lfs | 大文件支持（可选） | git-lfs --version |

## 配置文件

### 配置文件位置

```
skills/software/git-commit/config.json
```

### 配置项说明

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `default_branch` | string | "main" | 默认分支名称 |
| `default_remote` | string | "origin" | 默认远程仓库名称 |
| `auto_push` | boolean | false | 提交后自动推送到远程 |
| `require_confirmation` | boolean | true | 执行前需要用户确认 |
| `allowed_branches` | array | ["main", "develop", "feature/*", "bugfix/*", "hotfix/*"] | 允许提交的分支列表 |
| `protected_branches` | array | ["main", "master"] | 受保护的分支 |
| `file_patterns.exclude` | array | ["*.log", "*.tmp", ".env", "*.secret"] | 排除的文件模式 |
| `gpg_sign` | boolean | false | 默认使用 GPG 签名提交 |
| `dry_run_by_default` | boolean | false | 默认使用模拟模式 |

### 安全机制

| 安全机制 | 说明 |
|---------|------|
| **分支保护** | 受保护分支不允许直接提交 |
| **文件过滤** | 自动排除敏感文件 |
| **确认机制** | 执行前需要用户确认 |
| **GPG 签名** | 支持提交签名验证 |

详细配置说明请参考：[CONFIG.md](CONFIG.md)

## 失败分类
| 分类 | 说明 | 建议 |
|------|------|------|
| tool_missing | 缺少 Git 工具 | 安装 Git，检查 PATH |
| not_git_repo | 当前目录不是 Git 仓库 | 初始化仓库或切换到正确目录 |
| no_changes | 没有需要提交的变更 | 修改文件后再提交 |
| commit_error | 提交失败 | 查看详细错误信息 |
| push_error | 推送失败 | 检查远程仓库连接和权限 |
| config_error | 配置错误 | 检查配置参数是否正确 |

## 安全注意事项
- 确保提交信息准确描述变更内容
- 推送前确保有远程仓库的权限
- 重要提交建议使用 GPG 签名
- 敏感信息不要提交到仓库

## 参考资料
- [Git 官方文档](https://git-scm.com/docs)
- [Git Commit 规范](https://www.conventionalcommits.org/)
