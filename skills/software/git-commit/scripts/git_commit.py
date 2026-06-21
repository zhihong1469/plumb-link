#!/usr/bin/env python3
"""Git 代码提交和分支管理工具。

支持：
- 自动检测 Git 仓库状态
- 添加变更文件（全部/修改/指定）
- 生成提交信息
- 执行 git commit
- 推送到远程仓库
- GPG 签名提交
- 配置文件支持
- 分支保护检查
- 文件过滤
- 分支创建和切换
- 分支合并
- 分支删除
- 完整工作流支持
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


_SCRIPT_DIR = Path(__file__).resolve().parent
_SKILLS_DIR = _SCRIPT_DIR.parent.parent
_CONFIG_FILE = _SCRIPT_DIR.parent / "config.json"


@dataclass
class GitConfig:
    default_branch: str = "main"
    default_remote: str = "origin"
    auto_push: bool = False
    require_confirmation: bool = True
    commit_message_template: str = "{type}({scope}): {subject}"
    commit_message_types: list[str] = field(default_factory=lambda: ["feat", "fix", "docs", "style", "refactor", "test", "chore"])
    commit_message_type_descriptions: dict = field(default_factory=lambda: {
        "feat": "新增功能",
        "fix": "修复 bug",
        "docs": "修改文档",
        "style": "代码格式调整",
        "refactor": "重构代码",
        "test": "添加或修改测试",
        "chore": "构建流程、依赖管理等杂项"
    })
    commit_message_require_type: bool = True
    commit_message_require_scope: bool = False
    commit_message_require_subject: bool = True
    commit_message_subject_max_length: int = 50
    allowed_branches: list[str] = field(default_factory=lambda: ["main", "develop", "feature/*", "bugfix/*", "hotfix/*"])
    protected_branches: list[str] = field(default_factory=lambda: ["main", "master"])
    file_patterns_include: list[str] = field(default_factory=list)
    file_patterns_exclude: list[str] = field(default_factory=lambda: ["*.log", "*.tmp", ".env", "*.secret"])
    gpg_sign: bool = False
    dry_run_by_default: bool = False
    branch_auto_create: bool = False
    # 分支工作流配置
    main_branches: list[str] = field(default_factory=lambda: ["main", "release/*"])
    feature_branch_prefix: str = "feature/"
    bugfix_branch_prefix: str = "bugfix/"
    hotfix_branch_prefix: str = "hotfix/"
    auto_create_feature: bool = True
    auto_merge_to_main: bool = False
    auto_delete_after_merge: bool = False
    merge_strategy: str = "merge"
    require_pull_before_merge: bool = True
    confirm_before_delete: bool = True
    # 分支创建配置
    create_from_main_branch: bool = True
    pull_before_create: bool = True
    # 合并配置
    merge_target_branches: list[str] = field(default_factory=lambda: ["main", "release/*"])
    require_clean_working_tree: bool = True
    squash_merge: bool = False
    delete_source_after_merge: bool = False
    # 安全配置
    security_enabled: bool = False
    require_user_activation: bool = True
    activation_required_message: str = "此技能需要用户手动激活"
    allowed_operations: list[str] = field(default_factory=lambda: ["commit", "branch_create", "branch_switch", "pull", "merge", "push", "delete_branch"])
    blocked_operations: list[str] = field(default_factory=list)


@dataclass
class GitStatus:
    is_git_repo: bool
    branch: str | None
    remote: str | None
    modified_files: list[str] = field(default_factory=list)
    staged_files: list[str] = field(default_factory=list)
    untracked_files: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)


@dataclass
class CommitResult:
    status: str
    summary: str
    commit_hash: str | None = None
    branch: str | None = None
    committed_files: list[str] = field(default_factory=list)
    pushed: bool = False
    push_branch: str | None = None
    failure_category: str | None = None
    evidence: list[str] = field(default_factory=list)


def load_config() -> GitConfig:
    """加载配置文件。"""
    if not _CONFIG_FILE.exists():
        return GitConfig()

    try:
        with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        commit_msg_config = data.get("commit_message", {})
        branch_config = data.get("branch_creation", {})
        workflow_config = data.get("branch_workflow", {})
        merge_config = data.get("merge_config", {})
        security_config = data.get("security", {})
        
        return GitConfig(
            default_branch=data.get("default_branch", "main"),
            default_remote=data.get("default_remote", "origin"),
            auto_push=data.get("auto_push", False),
            require_confirmation=data.get("require_confirmation", True),
            commit_message_template=commit_msg_config.get("template", "{type}({scope}): {subject}"),
            commit_message_types=commit_msg_config.get("types", ["feat", "fix", "docs", "style", "refactor", "test", "chore"]),
            commit_message_type_descriptions=commit_msg_config.get("type_descriptions", {
                "feat": "新增功能",
                "fix": "修复 bug",
                "docs": "修改文档",
                "style": "代码格式调整",
                "refactor": "重构代码",
                "test": "添加或修改测试",
                "chore": "构建流程、依赖管理等杂项"
            }),
            commit_message_require_type=commit_msg_config.get("require_type", True),
            commit_message_require_scope=commit_msg_config.get("require_scope", False),
            commit_message_require_subject=commit_msg_config.get("require_subject", True),
            commit_message_subject_max_length=commit_msg_config.get("subject_max_length", 50),
            allowed_branches=data.get("allowed_branches", ["main", "develop", "feature/*", "bugfix/*", "hotfix/*"]),
            protected_branches=data.get("protected_branches", ["main", "master"]),
            file_patterns_include=data.get("file_patterns", {}).get("include", []),
            file_patterns_exclude=data.get("file_patterns", {}).get("exclude", ["*.log", "*.tmp", ".env", "*.secret"]),
            gpg_sign=data.get("gpg_sign", False),
            dry_run_by_default=data.get("dry_run_by_default", False),
            branch_auto_create=branch_config.get("auto_create", False),
            # 分支工作流配置
            main_branches=workflow_config.get("main_branches", ["main", "release/*"]),
            feature_branch_prefix=workflow_config.get("feature_branch_prefix", "feature/"),
            bugfix_branch_prefix=workflow_config.get("bugfix_branch_prefix", "bugfix/"),
            hotfix_branch_prefix=workflow_config.get("hotfix_branch_prefix", "hotfix/"),
            auto_create_feature=workflow_config.get("auto_create_feature", True),
            auto_merge_to_main=workflow_config.get("auto_merge_to_main", False),
            auto_delete_after_merge=workflow_config.get("auto_delete_after_merge", False),
            merge_strategy=workflow_config.get("merge_strategy", "merge"),
            require_pull_before_merge=workflow_config.get("require_pull_before_merge", True),
            confirm_before_delete=workflow_config.get("confirm_before_delete", True),
            # 分支创建配置
            create_from_main_branch=branch_config.get("from_main_branch", True),
            pull_before_create=branch_config.get("pull_before_create", True),
            # 合并配置
            merge_target_branches=merge_config.get("target_branches", ["main", "release/*"]),
            require_clean_working_tree=merge_config.get("require_clean_working_tree", True),
            squash_merge=merge_config.get("squash_merge", False),
            delete_source_after_merge=merge_config.get("delete_source_after_merge", False),
            # 安全配置
            security_enabled=security_config.get("enabled", False),
            require_user_activation=security_config.get("require_user_activation", True),
            activation_required_message=security_config.get("activation_required_message", "此技能需要用户手动激活"),
            allowed_operations=security_config.get("allowed_operations", ["commit", "branch_create", "branch_switch", "pull", "merge", "push", "delete_branch"]),
            blocked_operations=security_config.get("blocked_operations", []),
        )
    except Exception as e:
        print(f"⚠️ 加载配置文件失败: {e}")
        return GitConfig()


def check_security_enabled(config: GitConfig) -> tuple[bool, str]:
    """检查技能是否已启用。"""
    if config.require_user_activation and not config.security_enabled:
        return False, config.activation_required_message
    return True, ""


def parse_commit_message(message: str, config: GitConfig) -> tuple[bool, str, dict | None]:
    """解析提交消息，验证格式是否符合规范。"""
    if not message:
        return False, "提交消息不能为空", None
    
    # 尝试解析格式：type(scope): subject
    import re
    pattern = r"^(\w+)(?:\(([^)]+)\))?:\s*(.+)$"
    match = re.match(pattern, message)
    
    if not match:
        return False, f"提交消息格式不正确，应为: {config.commit_message_template}", None
    
    commit_type = match.group(1)
    scope = match.group(2)
    subject = match.group(3).strip()
    
    # 验证 type
    if config.commit_message_require_type and commit_type not in config.commit_message_types:
        types_str = ", ".join(config.commit_message_types)
        return False, f"无效的类型 '{commit_type}'，可选类型: {types_str}", None
    
    # 验证 scope（如果要求）
    if config.commit_message_require_scope and not scope:
        return False, "缺少 scope（作用范围）", None
    
    # 验证 subject
    if config.commit_message_require_subject and not subject:
        return False, "缺少 subject（简短描述）", None
    
    if subject and len(subject) > config.commit_message_subject_max_length:
        return False, f"subject 长度超过 {config.commit_message_subject_max_length} 字符", None
    
    # 验证 subject 格式
    if subject:
        if subject[0].isupper():
            return False, "subject 首字母应小写", None
        if subject.endswith("."):
            return False, "subject 结尾不应加句号", None
    
    return True, "格式验证通过", {
        "type": commit_type,
        "scope": scope,
        "subject": subject,
        "type_description": config.commit_message_type_descriptions.get(commit_type)
    }


def format_commit_message(config: GitConfig, commit_type: str, scope: str | None = None, subject: str = "") -> str:
    """根据模板格式化提交消息。"""
    return config.commit_message_template.format(
        type=commit_type,
        scope=scope if scope else "",
        subject=subject
    )


def create_branch(branch_name: str, from_branch: str | None = None, 
                  cwd: str | None = None) -> tuple[bool, str, str]:
    """创建新分支。"""
    # 首先检查是否有初始提交
    code, _, _ = run_git_command(["rev-parse", "HEAD"], cwd=cwd)
    if code != 0:
        # 没有初始提交，需要先初始化分支
        print("ℹ️ 仓库没有初始提交，先创建初始提交...")
        
        # 检查是否有文件
        code_ls, ls_output, _ = run_git_command(["ls-files", "--cached"], cwd=cwd)
        if code_ls == 0 and ls_output == "":
            # 没有暂存文件，尝试添加所有文件
            print("   添加所有文件到暂存区...")
            run_git_command(["add", "-A"], cwd=cwd)
        
        # 创建初始提交
        code_commit, _, stderr_commit = run_git_command(
            ["commit", "-m", "initial commit", "--allow-empty"], 
            cwd=cwd
        )
        if code_commit != 0:
            return False, "", f"无法创建初始提交: {stderr_commit}"
    
    # 先切换到源分支（如果指定）
    if from_branch:
        print(f"   切换到源分支: {from_branch}")
        code_switch, _, stderr_switch = run_git_command(["checkout", from_branch], cwd=cwd)
        if code_switch != 0:
            return False, "", f"无法切换到源分支 {from_branch}: {stderr_switch}"
    
    # 创建新分支
    args = ["checkout", "-b", branch_name]
    code, stdout, stderr = run_git_command(args, cwd=cwd)
    if code != 0:
        return False, "", stderr or "创建分支失败"
    
    # 验证分支是否正确创建
    code_verify, branch_output, _ = run_git_command(["branch", "--show-current"], cwd=cwd)
    if code_verify == 0 and branch_output == branch_name:
        return True, branch_name, stdout
    else:
        # 分支创建可能有问题，尝试另一种方式
        print("⚠️ 分支验证失败，尝试使用 git branch 命令创建...")
        code_create, _, stderr_create = run_git_command(["branch", branch_name], cwd=cwd)
        if code_create == 0:
            # 创建成功，切换到新分支
            run_git_command(["checkout", branch_name], cwd=cwd)
            return True, branch_name, "使用 git branch 命令创建分支"
        return False, "", f"分支创建验证失败: {stderr_create}"


def switch_branch(branch_name: str, cwd: str | None = None) -> tuple[bool, str, str]:
    """切换到指定分支。"""
    code, stdout, stderr = run_git_command(["checkout", branch_name], cwd=cwd)
    if code != 0:
        return False, "", stderr or "切换分支失败"
    
    return True, branch_name, stdout


def pull_branch(remote: str, branch: str | None = None, 
                cwd: str | None = None) -> tuple[bool, str, str]:
    """拉取远程分支最新代码。"""
    args = ["pull"]
    if branch:
        args.extend([remote, branch])
    else:
        args.append(remote)
    
    code, stdout, stderr = run_git_command(args, cwd=cwd)
    if code != 0:
        return False, "", stderr or "拉取失败"
    
    return True, stdout, stdout


def merge_branch(source_branch: str, target_branch: str, 
                 squash: bool = False, cwd: str | None = None) -> tuple[bool, str, str]:
    """合并分支。"""
    # 先切换到目标分支
    success, _, msg = switch_branch(target_branch, cwd=cwd)
    if not success:
        return False, "", f"切换到目标分支失败: {msg}"
    
    # 执行合并
    args = ["merge", source_branch]
    if squash:
        args.append("--squash")
    
    code, stdout, stderr = run_git_command(args, cwd=cwd)
    if code != 0:
        return False, "", stderr or "合并失败"
    
    return True, stdout, stdout


def delete_branch(branch_name: str, force: bool = False, 
                  cwd: str | None = None) -> tuple[bool, str, str]:
    """删除分支。"""
    args = ["branch", "-d" if not force else "-D", branch_name]
    
    code, stdout, stderr = run_git_command(args, cwd=cwd)
    if code != 0:
        return False, "", stderr or "删除分支失败"
    
    return True, branch_name, stdout


def push_branch(remote: str, branch: str, 
                 set_upstream: bool = False, cwd: str | None = None) -> tuple[bool, str, str]:
    """推送分支到远程。"""
    args = ["push"]
    if set_upstream:
        args.extend(["-u", remote, branch])
    else:
        args.extend([remote, branch])
    
    code, stdout, stderr = run_git_command(args, cwd=cwd)
    if code != 0:
        return False, "", stderr or "推送失败"
    
    return True, branch, stdout


def get_main_branch(config: GitConfig, cwd: str | None = None) -> str | None:
    """获取当前匹配的主分支。"""
    code, branches_output, _ = run_git_command(["branch", "-a"], cwd=cwd)
    if code != 0:
        return config.default_branch
    
    # 检查当前分支是否匹配主分支模式
    for branch_pattern in config.main_branches:
        for line in branches_output.split("\n"):
            branch = line.strip().replace("* ", "").replace("remotes/origin/", "")
            if fnmatch.fnmatch(branch, branch_pattern):
                return branch
    
    return config.default_branch


def check_working_tree_clean(cwd: str | None = None) -> tuple[bool, list[str]]:
    """检查工作区是否干净。"""
    code, status_output, _ = run_git_command(["status", "--porcelain"], cwd=cwd)
    if code != 0:
        return False, ["无法获取工作区状态"]
    
    changes = [line.strip() for line in status_output.split("\n") if line.strip()]
    return len(changes) == 0, changes


def check_branch_protection(branch: str | None, config: GitConfig) -> tuple[bool, str]:
    """检查分支保护。"""
    if not branch:
        return True, ""
    
    for protected in config.protected_branches:
        if fnmatch.fnmatch(branch, protected):
            return False, f"分支 '{branch}' 受保护，不允许直接提交"
    
    return True, ""


def check_branch_allowed(branch: str | None, config: GitConfig) -> tuple[bool, str]:
    """检查分支是否允许提交。"""
    if not branch:
        return True, ""
    
    for allowed in config.allowed_branches:
        if fnmatch.fnmatch(branch, allowed):
            return True, ""
    
    return False, f"分支 '{branch}' 不在允许列表中"


def filter_files(files: list[str], config: GitConfig) -> list[str]:
    """根据配置过滤文件。"""
    filtered = []
    
    for file in files:
        # 检查排除模式
        excluded = False
        for pattern in config.file_patterns_exclude:
            if fnmatch.fnmatch(file, pattern):
                excluded = True
                break
        
        if excluded:
            continue
        
        # 检查包含模式
        if config.file_patterns_include:
            included = False
            for pattern in config.file_patterns_include:
                if fnmatch.fnmatch(file, pattern):
                    included = True
                    break
            
            if not included:
                continue
        
        filtered.append(file)
    
    return filtered


def run_git_command(args: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    """执行 Git 命令。"""
    try:
        full_command = ["git"] + args
        print(f"🔧 执行命令: {' '.join(full_command)}")
        if cwd:
            print(f"   工作目录: {cwd}")
        
        result = subprocess.run(
            full_command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        
        if result.returncode != 0:
            print(f"⚠️ 命令返回错误码: {result.returncode}")
            if result.stderr:
                print(f"   错误信息: {result.stderr}")
        
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        print("⏰ 命令执行超时")
        return -1, "", "命令超时"
    except Exception as e:
        print(f"❌ 命令执行异常: {e}")
        return -1, "", f"执行异常: {e}"


def detect_git() -> bool:
    """检测 Git 是否可用。"""
    code, _, _ = run_git_command(["--version"])
    return code == 0


def is_git_repo(cwd: str | None = None) -> bool:
    """检查当前目录是否为 Git 仓库。"""
    code, _, _ = run_git_command(["rev-parse", "--is-inside-work-tree"], cwd=cwd)
    return code == 0


def get_git_status(cwd: str | None = None) -> GitStatus:
    """获取 Git 仓库状态。"""
    if not is_git_repo(cwd):
        return GitStatus(is_git_repo=False, branch=None, remote=None)

    status = GitStatus(is_git_repo=True, branch=None, remote=None)

    code, branch_output, _ = run_git_command(["branch", "--show-current"], cwd=cwd)
    if code == 0:
        status.branch = branch_output

    code, remote_output, _ = run_git_command(["remote", "get-url", "origin"], cwd=cwd)
    if code == 0:
        status.remote = remote_output

    code, status_output, _ = run_git_command(["status", "--porcelain"], cwd=cwd)
    if code == 0:
        for line in status_output.split("\n"):
            if not line.strip():
                continue
            prefix = line[:2].strip()
            filename = line[3:].strip()

            if prefix == "M":
                status.modified_files.append(filename)
            elif prefix == "A":
                status.staged_files.append(filename)
            elif prefix == "??":
                status.untracked_files.append(filename)
            elif "U" in prefix or "D" in prefix:
                status.conflicts.append(filename)

    return status


def add_files(add_mode: str, files: list[str] | None = None, cwd: str | None = None) -> tuple[bool, list[str], str]:
    """添加文件到暂存区。"""
    committed_files = []

    if add_mode == "none":
        return True, committed_files, "未添加任何文件"

    if add_mode == "all":
        code, stdout, stderr = run_git_command(["add", "-A"], cwd=cwd)
        if code != 0:
            return False, [], stderr or "添加文件失败"
        committed_files = ["所有变更文件"]
        return True, committed_files, stdout

    if add_mode == "modified":
        code, stdout, stderr = run_git_command(["add", "-u"], cwd=cwd)
        if code != 0:
            return False, [], stderr or "添加修改文件失败"
        committed_files = ["所有修改文件"]
        return True, committed_files, stdout

    if files:
        code, stdout, stderr = run_git_command(["add"] + files, cwd=cwd)
        if code != 0:
            return False, [], stderr or "添加指定文件失败"
        committed_files = files
        return True, committed_files, stdout

    return True, committed_files, ""


def get_commit_message(message: str | None, message_file: str | None) -> str | None:
    """获取提交信息。"""
    if message:
        return message

    if message_file and Path(message_file).exists():
        try:
            return Path(message_file).read_text(encoding="utf-8").strip()
        except Exception as e:
            print(f"⚠️ 无法读取提交信息文件: {e}")
            return None

    return None


def execute_commit(message: str, amend: bool = False, sign: bool = False, 
                   dry_run: bool = False, cwd: str | None = None) -> tuple[bool, str, str]:
    """执行 git commit。"""
    args = ["commit", "-m", message]
    if amend:
        args.append("--amend")
    if sign:
        args.append("-S")
    if dry_run:
        args.append("--dry-run")

    # 获取提交前的 HEAD
    before_hash = None
    if not dry_run:
        code_before, before_hash, _ = run_git_command(["rev-parse", "HEAD"], cwd=cwd)
        if code_before != 0:
            before_hash = None

    code, stdout, stderr = run_git_command(args, cwd=cwd)
    
    if code != 0:
        return False, "", stderr or "提交失败"

    commit_hash = None
    if not dry_run:
        # 获取提交后的 HEAD
        code_hash, hash_output, _ = run_git_command(["rev-parse", "HEAD"], cwd=cwd)
        if code_hash == 0:
            commit_hash = hash_output
            
            # 验证提交是否真正发生
            if before_hash == commit_hash:
                print("⚠️ 警告：提交前后 HEAD 相同，可能提交未成功")
                # 检查是否有错误
                if not stdout:
                    return False, "", "提交未成功，HEAD 没有变化"
        
        if not commit_hash:
            print("❌ 错误：无法获取提交哈希值")
            return False, "", "无法获取提交哈希值"

    return True, commit_hash or "", stdout


def execute_push(remote: str, branch: str | None = None, dry_run: bool = False, 
                 cwd: str | None = None) -> tuple[bool, str, str]:
    """执行 git push。"""
    args = ["push"]
    if dry_run:
        args.append("--dry-run")
    
    if branch:
        args.extend([remote, branch])
    else:
        args.append(remote)

    code, stdout, stderr = run_git_command(args, cwd=cwd)
    if code != 0:
        return False, "", stderr or "推送失败"

    push_branch = branch or "当前分支"
    return True, push_branch, stdout


def result_to_json(result: CommitResult) -> str:
    """将提交结果转为 JSON。"""
    data = {
        "status": result.status,
        "summary": result.summary,
        "commit_hash": result.commit_hash,
        "branch": result.branch,
        "committed_files": result.committed_files,
        "pushed": result.pushed,
        "push_branch": result.push_branch,
        "failure_category": result.failure_category,
        "evidence": result.evidence,
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


def handle_workflow(args, config: GitConfig, cwd: str):
    """处理预定义工作流。"""
    workflow_type = args.workflow
    
    print(f"\n🔄 执行工作流: {workflow_type}")
    
    if workflow_type == "feature":
        # 创建功能分支工作流
        if not args.feature_name:
            print("   ❌ 缺少功能分支名称，请使用 --feature-name 指定")
            return
        
        # 确定分支名称
        branch_name = f"{config.feature_branch_prefix}{args.feature_name}"
        
        # 确定从哪个分支创建
        from_branch = args.from_branch or get_main_branch(config, cwd)
        
        print(f"   功能分支: {branch_name}")
        print(f"   从分支: {from_branch}")
        
        # 1. 拉取最新代码
        if config.pull_before_create:
            print("\n   步骤 1: 拉取最新代码")
            pull_success, _, pull_msg = pull_branch(args.remote, from_branch, cwd)
            if pull_success:
                print(f"   ✓ 已拉取 {from_branch} 最新代码")
            else:
                print(f"   ⚠️ 拉取失败: {pull_msg}")
        
        # 2. 创建功能分支
        print("\n   步骤 2: 创建功能分支")
        create_success, _, create_msg = create_branch(branch_name, from_branch, cwd)
        if create_success:
            print(f"   ✓ 已创建分支: {branch_name}")
        else:
            print(f"   ❌ 创建失败: {create_msg}")
            return
        
        # 3. 推送到远程（可选）
        if args.set_upstream:
            print("\n   步骤 3: 推送到远程")
            push_success, _, push_msg = push_branch(args.remote, branch_name, set_upstream=True, cwd=cwd)
            if push_success:
                print(f"   ✓ 已推送 {branch_name} 到远程")
            else:
                print(f"   ⚠️ 推送失败: {push_msg}")
        
        print(f"\n✅ 功能分支工作流完成")
        print(f"   当前分支: {branch_name}")
        print(f"   下一步: 开发功能并提交代码")
    
    elif workflow_type == "merge":
        # 合并工作流
        git_status = get_git_status(cwd)
        source_branch = git_status.branch
        
        if not source_branch:
            print("   ❌ 无法获取当前分支")
            return
        
        # 确定目标分支
        target_branch = args.target_release or args.merge_to
        if not target_branch:
            target_branch = get_main_branch(config, cwd)
        
        print(f"   源分支: {source_branch}")
        print(f"   目标分支: {target_branch}")
        
        # 1. 检查工作区是否干净
        if config.require_clean_working_tree:
            clean, changes = check_working_tree_clean(cwd)
            if not clean:
                print(f"   ⚠️ 工作区不干净，请先提交变更")
                return
        
        # 2. 拉取目标分支最新代码
        if config.require_pull_before_merge:
            print("\n   步骤 1: 拉取目标分支最新代码")
            switch_success, _, switch_msg = switch_branch(target_branch, cwd)
            if switch_success:
                pull_success, _, pull_msg = pull_branch(args.remote, target_branch, cwd)
                if pull_success:
                    print(f"   ✓ 已拉取 {target_branch} 最新代码")
                else:
                    print(f"   ⚠️ 拉取失败: {pull_msg}")
            else:
                print(f"   ⚠️ 切换失败: {switch_msg}")
        
        # 3. 合并
        print("\n   步骤 2: 合并分支")
        merge_success, _, merge_msg = merge_branch(source_branch, target_branch, config.squash_merge, cwd)
        if merge_success:
            print(f"   ✓ 已合并 {source_branch} 到 {target_branch}")
        else:
            print(f"   ❌ 合并失败: {merge_msg}")
            return
        
        # 4. 推送
        print("\n   步骤 3: 推送合并结果")
        push_success, _, push_msg = push_branch(args.remote, target_branch, cwd=cwd)
        if push_success:
            print(f"   ✓ 已推送 {target_branch} 到远程")
        else:
            print(f"   ⚠️ 推送失败: {push_msg}")
        
        # 5. 删除源分支（可选）
        if args.delete_after_merge or config.delete_source_after_merge:
            print("\n   步骤 4: 删除源分支")
            delete_success, _, delete_msg = delete_branch(source_branch, cwd=cwd)
            if delete_success:
                print(f"   ✓ 已删除分支: {source_branch}")
            else:
                print(f"   ⚠️ 删除失败: {delete_msg}")
        
        print(f"\n✅ 合并工作流完成")
    
    elif workflow_type == "complete":
        # 完整工作流：创建分支 -> 开发 -> 合并 -> 删除
        print("   完整工作流需要分步执行:")
        print("   1. --workflow feature --feature-name <name>  # 创建功能分支")
        print("   2. 开发并提交代码")
        print("   3. --workflow merge --target-release <branch> --delete-after-merge  # 合并并删除")
    
    else:
        print(f"   ❌ 未知工作流类型: {workflow_type}")


def main():
    parser = argparse.ArgumentParser(description="Git 代码提交和分支管理工具")
    
    # 提交相关参数
    parser.add_argument("--message", "-m", type=str, help="提交信息")
    parser.add_argument("--message-file", "-F", type=str, help="提交信息文件路径")
    parser.add_argument(
        "--add", type=str, choices=["all", "modified", "none"], default="all",
        help="添加文件模式 (all/modified/none)"
    )
    parser.add_argument("--files", type=str, nargs="*", help="指定提交的文件列表")
    parser.add_argument("--amend", action="store_true", help="修改上次提交")
    parser.add_argument("--push", action="store_true", help="提交后推送到远程")
    parser.add_argument("--branch", type=str, help="指定分支")
    parser.add_argument("--remote", type=str, default="origin", help="远程仓库名称")
    parser.add_argument("--sign", "-S", action="store_true", help="GPG 签名提交")
    parser.add_argument("--dry-run", action="store_true", help="模拟执行，不实际提交")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式结果")
    parser.add_argument("--cwd", type=str, help="工作目录")
    
    # 分支管理参数
    parser.add_argument("--create-branch", type=str, metavar="NAME", help="创建新分支")
    parser.add_argument("--from-branch", type=str, metavar="BRANCH", help="从指定分支创建新分支")
    parser.add_argument("--switch-branch", type=str, metavar="NAME", help="切换到指定分支")
    parser.add_argument("--pull", action="store_true", help="拉取远程最新代码")
    parser.add_argument("--merge-to", type=str, metavar="BRANCH", help="合并当前分支到指定分支")
    parser.add_argument("--delete-branch", type=str, metavar="NAME", help="删除指定分支")
    parser.add_argument("--force-delete", action="store_true", help="强制删除分支")
    parser.add_argument("--set-upstream", action="store_true", help="推送时设置上游分支")
    
    # 工作流参数
    parser.add_argument("--workflow", type=str, choices=["feature", "bugfix", "hotfix", "merge", "complete"], 
                        help="执行预定义工作流")
    parser.add_argument("--feature-name", type=str, metavar="NAME", help="功能分支名称（用于 workflow）")
    parser.add_argument("--target-release", type=str, metavar="BRANCH", help="目标发布分支（用于 merge workflow）")
    parser.add_argument("--delete-after-merge", action="store_true", help="合并后删除源分支")

    args = parser.parse_args()

    # 加载配置文件
    config = load_config()

    # 应用配置默认值
    if args.remote == "origin" and config.default_remote != "origin":
        args.remote = config.default_remote
    if not args.push and config.auto_push:
        args.push = config.auto_push
    if not args.sign and config.gpg_sign:
        args.sign = config.gpg_sign
    if not args.dry_run and config.dry_run_by_default:
        args.dry_run = config.dry_run_by_default

    evidence = []

    if not detect_git():
        result = CommitResult(
            status="failure",
            summary="Git 工具不可用",
            failure_category="tool_missing",
            evidence=["未检测到 Git 工具，请安装 Git"],
        )
        if args.json:
            print(result_to_json(result))
        else:
            print(f"❌ {result.summary}")
        return

    cwd = args.cwd or os.getcwd()

    # 安全检查：技能是否已启用
    security_enabled, security_message = check_security_enabled(config)
    if not security_enabled:
        result = CommitResult(
            status="failure",
            summary="技能未激活",
            failure_category="security_error",
            evidence=[security_message, 
                      f"配置文件路径: {_CONFIG_FILE}",
                      "请手动查看并修改配置文件以启用此技能"],
        )
        if args.json:
            print(result_to_json(result))
        else:
            print("🔒 ===============================================")
            print("🔒 安全警告：此技能需要用户手动激活")
            print("🔒 ===============================================")
            print(f"\n❌ {security_message}")
            print(f"\n📋 请按照以下步骤激活：")
            print(f"   1. 查看配置文件: {_CONFIG_FILE}")
            print(f"   2. 将 security.enabled 设置为 true")
            print(f"   3. 确认所有配置项符合您的需求")
            print(f"\n🔒 安全说明：")
            print(f"   - 此技能涉及代码提交和分支管理操作")
            print(f"   - 必须由用户手动确认后才能使用")
            print(f"   - 大模型无法自动修改此开关")
            print("🔒 ===============================================")
        return

    # 处理分支管理命令
    if args.create_branch:
        print(f"\n🌿 创建新分支: {args.create_branch}")
        
        # 确定从哪个分支创建
        from_branch = args.from_branch
        if not from_branch and config.create_from_main_branch:
            from_branch = get_main_branch(config, cwd)
        
        if from_branch:
            print(f"   从分支: {from_branch}")
            # 如果配置要求，先拉取最新代码
            if config.pull_before_create:
                print("   正在拉取最新代码...")
                pull_success, pull_output, pull_error = pull_branch(args.remote, from_branch, cwd)
                if pull_success:
                    print(f"   ✓ 已拉取最新代码")
                else:
                    print(f"   ⚠️ 拉取失败: {pull_error}")
        
        success, branch_name, msg = create_branch(args.create_branch, from_branch, cwd)
        if success:
            print(f"   ✓ 已创建并切换到分支: {branch_name}")
            if args.set_upstream:
                push_success, _, push_msg = push_branch(args.remote, branch_name, set_upstream=True, cwd=cwd)
                if push_success:
                    print(f"   ✓ 已推送到远程: {args.remote}/{branch_name}")
                else:
                    print(f"   ⚠️ 推送失败: {push_msg}")
        else:
            print(f"   ❌ 创建失败: {msg}")
        return

    if args.switch_branch:
        print(f"\n🌿 切换分支: {args.switch_branch}")
        success, branch_name, msg = switch_branch(args.switch_branch, cwd)
        if success:
            print(f"   ✓ 已切换到分支: {branch_name}")
        else:
            print(f"   ❌ 切换失败: {msg}")
        return

    if args.pull:
        print(f"\n⬇️ 拉取最新代码")
        git_status = get_git_status(cwd)
        branch = git_status.branch or args.branch
        print(f"   分支: {branch}")
        print(f"   远程: {args.remote}")
        success, output, msg = pull_branch(args.remote, branch, cwd)
        if success:
            print(f"   ✓ 已拉取最新代码")
            print(f"   {output}")
        else:
            print(f"   ❌ 拉取失败: {msg}")
        return

    if args.merge_to:
        print(f"\n🔀 合并分支")
        git_status = get_git_status(cwd)
        source_branch = git_status.branch
        
        if not source_branch:
            print("   ❌ 无法获取当前分支")
            return
        
        print(f"   源分支: {source_branch}")
        print(f"   目标分支: {args.merge_to}")
        
        # 检查工作区是否干净
        if config.require_clean_working_tree:
            clean, changes = check_working_tree_clean(cwd)
            if not clean:
                print(f"   ⚠️ 工作区不干净，有以下变更:")
                for change in changes:
                    print(f"     - {change}")
                print("   请先提交或暂存变更后再合并")
                return
        
        success, output, msg = merge_branch(source_branch, args.merge_to, config.squash_merge, cwd)
        if success:
            print(f"   ✓ 已合并 {source_branch} 到 {args.merge_to}")
            
            # 推送合并结果
            push_success, _, push_msg = push_branch(args.remote, args.merge_to, cwd=cwd)
            if push_success:
                print(f"   ✓ 已推送 {args.merge_to} 到远程")
            else:
                print(f"   ⚠️ 推送失败: {push_msg}")
            
            # 删除源分支（如果指定）
            if args.delete_after_merge or config.delete_source_after_merge:
                if config.confirm_before_delete:
                    print(f"\n   是否删除源分支 {source_branch}? (y/n)")
                    # 这里需要用户确认，但脚本中无法交互，所以直接删除
                    print(f"   正在删除分支 {source_branch}...")
                
                delete_success, _, delete_msg = delete_branch(source_branch, cwd=cwd)
                if delete_success:
                    print(f"   ✓ 已删除分支: {source_branch}")
                else:
                    print(f"   ⚠️ 删除失败: {delete_msg}")
        else:
            print(f"   ❌ 合并失败: {msg}")
        return

    if args.delete_branch:
        print(f"\n🗑️ 删除分支: {args.delete_branch}")
        
        # 检查是否是受保护分支
        protected, protected_msg = check_branch_protection(args.delete_branch, config)
        if not protected:
            print(f"   ❌ {protected_msg}")
            return
        
        if config.confirm_before_delete and not args.force_delete:
            print(f"   ⚠️ 是否确认删除分支 {args.delete_branch}? (使用 --force-delete 强制删除)")
            return
        
        success, branch_name, msg = delete_branch(args.delete_branch, args.force_delete, cwd)
        if success:
            print(f"   ✓ 已删除分支: {branch_name}")
        else:
            print(f"   ❌ 删除失败: {msg}")
        return

    # 处理预定义工作流
    if args.workflow:
        handle_workflow(args, config, cwd)
        return

    git_status = get_git_status(cwd)
    if not git_status.is_git_repo:
        result = CommitResult(
            status="failure",
            summary="当前目录不是 Git 仓库",
            failure_category="not_git_repo",
            evidence=[f"目录: {cwd}"],
        )
        if args.json:
            print(result_to_json(result))
        else:
            print(f"❌ {result.summary}")
        return

    print(f"📁 当前仓库: {cwd}")
    print(f"🌿 当前分支: {git_status.branch or '未知'}")
    if git_status.remote:
        print(f"🔗 远程仓库: {git_status.remote}")

    # 检查分支保护
    if git_status.branch:
        protected, protected_msg = check_branch_protection(git_status.branch, config)
        if not protected:
            result = CommitResult(
                status="failure",
                summary="分支受保护",
                failure_category="commit_error",
                evidence=[protected_msg],
            )
            if args.json:
                print(result_to_json(result))
            else:
                print(f"❌ {result.summary}")
                print(f"   {protected_msg}")
            return

        # 检查分支是否允许
        allowed, allowed_msg = check_branch_allowed(git_status.branch, config)
        if not allowed:
            result = CommitResult(
                status="failure",
                summary="分支不允许提交",
                failure_category="commit_error",
                evidence=[allowed_msg],
            )
            if args.json:
                print(result_to_json(result))
            else:
                print(f"❌ {result.summary}")
                print(f"   {allowed_msg}")
            return

    if git_status.conflicts:
        result = CommitResult(
            status="failure",
            summary="存在冲突文件，无法提交",
            failure_category="commit_error",
            evidence=[f"冲突文件: {', '.join(git_status.conflicts)}"],
        )
        if args.json:
            print(result_to_json(result))
        else:
            print(f"❌ {result.summary}")
            for f in git_status.conflicts:
                print(f"   - {f}")
        return

    print("\n📋 变更状态:")
    
    # 过滤文件
    filtered_modified = filter_files(git_status.modified_files, config)
    filtered_untracked = filter_files(git_status.untracked_files, config)
    
    if git_status.modified_files:
        print(f"   修改: {len(git_status.modified_files)} 个文件", end="")
        if len(filtered_modified) < len(git_status.modified_files):
            print(f" (过滤后: {len(filtered_modified)} 个)")
        else:
            print()
    if git_status.untracked_files:
        print(f"   新增: {len(git_status.untracked_files)} 个文件", end="")
        if len(filtered_untracked) < len(git_status.untracked_files):
            print(f" (过滤后: {len(filtered_untracked)} 个)")
        else:
            print()
    if git_status.staged_files:
        print(f"   已暂存: {len(git_status.staged_files)} 个文件")

    if not git_status.modified_files and not git_status.untracked_files and not git_status.staged_files:
        if not args.amend:
            result = CommitResult(
                status="failure",
                summary="没有需要提交的变更",
                failure_category="no_changes",
                evidence=["工作区干净，没有修改"],
            )
            if args.json:
                print(result_to_json(result))
            else:
                print(f"ℹ️ {result.summary}")
            return

    commit_message = get_commit_message(args.message, args.message_file)
    if not commit_message:
        result = CommitResult(
            status="failure",
            summary="提交信息不能为空",
            failure_category="config_error",
            evidence=["请使用 --message 或 --message-file 指定提交信息"],
        )
        if args.json:
            print(result_to_json(result))
        else:
            print(f"❌ {result.summary}")
            print("   提交消息格式示例:")
            print("   - feat(skill): add git commit skill")
            print("   - fix(build): fix compile error")
            print("   - docs(readme): update installation guide")
        return

    # 验证提交消息格式
    valid, msg, parsed = parse_commit_message(commit_message, config)
    if not valid:
        result = CommitResult(
            status="failure",
            summary="提交消息格式错误",
            failure_category="config_error",
            evidence=[msg],
        )
        if args.json:
            print(result_to_json(result))
        else:
            print(f"❌ {result.summary}")
            print(f"   {msg}")
            print("\n   提交消息格式规范:")
            print("   type(scope): subject")
            print("\n   type 可选值:")
            for t, desc in config.commit_message_type_descriptions.items():
                print(f"     {t}: {desc}")
            print("\n   示例:")
            print("     feat(skill): add git commit skill")
            print("     fix(build): fix compile error")
        return

    # 显示解析结果
    if parsed:
        print(f"\n📝 提交信息解析:")
        print(f"   类型: {parsed['type']} ({parsed.get('type_description', '')})")
        if parsed["scope"]:
            print(f"   范围: {parsed['scope']}")
        print(f"   描述: {parsed['subject']}")

    add_success, committed_files, add_output = add_files(args.add, args.files, cwd)
    if not add_success:
        result = CommitResult(
            status="failure",
            summary="添加文件失败",
            failure_category="commit_error",
            evidence=[add_output],
        )
        if args.json:
            print(result_to_json(result))
        else:
            print(f"❌ {result.summary}: {add_output}")
        return

    if add_output:
        evidence.append(f"添加文件: {add_output}")

    print(f"\n📝 提交信息: {commit_message}")

    commit_success, commit_hash, commit_output = execute_commit(
        commit_message, amend=args.amend, sign=args.sign, dry_run=args.dry_run, cwd=cwd
    )

    if not commit_success:
        result = CommitResult(
            status="failure",
            summary="提交失败",
            failure_category="commit_error",
            evidence=[commit_output],
        )
        if args.json:
            print(result_to_json(result))
        else:
            print(f"❌ {result.summary}")
            print(f"   错误: {commit_output}")
        return

    if commit_output:
        evidence.append(f"提交输出: {commit_output}")

    pushed = False
    push_branch = None

    if args.push:
        push_success, push_branch, push_output = execute_push(
            args.remote, args.branch or git_status.branch, dry_run=args.dry_run, cwd=cwd
        )
        if push_success:
            pushed = True
            evidence.append(f"推送输出: {push_output}")
        else:
            result = CommitResult(
                status="partial",
                summary="提交成功但推送失败",
                commit_hash=commit_hash,
                branch=git_status.branch,
                committed_files=committed_files,
                pushed=False,
                failure_category="push_error",
                evidence=evidence + [push_output],
            )
            if args.json:
                print(result_to_json(result))
            else:
                print(f"\n⚠️ {result.summary}")
                print(f"   提交哈希: {commit_hash}")
                print(f"   错误: {push_output}")
            return

    result = CommitResult(
        status="success",
        summary="提交成功" + ("并已推送" if pushed else ""),
        commit_hash=commit_hash,
        branch=git_status.branch,
        committed_files=committed_files,
        pushed=pushed,
        push_branch=push_branch,
        evidence=evidence,
    )

    if args.json:
        print(result_to_json(result))
    else:
        print(f"\n✅ {result.summary}")
        if commit_hash:
            print(f"   提交哈希: {commit_hash}")
        if committed_files:
            print(f"   提交文件: {', '.join(committed_files)}")
        if pushed:
            print(f"   推送到: {args.remote}/{push_branch}")


if __name__ == "__main__":
    main()
