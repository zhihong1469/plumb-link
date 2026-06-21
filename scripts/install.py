#!/usr/bin/env python3
"""Plumb-Link 技能安装器。

将技能从 plumb-link 安装到目标软件工程项目。

用法：
    python scripts/install.py /path/to/project                      # 安装全部技能
    python scripts/install.py /path/to/project --skills build-linux-app gpio-config
    python scripts/install.py /path/to/project --force              # 强制覆盖
    python scripts/install.py /path/to/project --detect            # 安装后探测工具路径
    python scripts/install.py /path/to/project --uninstall          # 卸载全部技能
    python scripts/install.py /path/to/project --remove build-linux-app  # 删除单个技能
    python scripts/install.py /path/to/project --status             # 查看安装状态
    python scripts/install.py --list                                # 列出可用技能
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# 设置标准输出编码
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

# 仓库路径
REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_SRC = REPO_ROOT / "skills"
SHARED_SRC = REPO_ROOT / "shared"
AGENTS_SRC = REPO_ROOT / "agents"
RULES_SRC = REPO_ROOT / "rules"
DESIGN_PLANNING_SRC = REPO_ROOT / "design_planning.md"

# 安装元数据文件名
META_FILENAME = ".em_skill_meta.json"
TOOL_CONFIG_FILENAME = ".em_skill.json"

# 跳过的文件模式
SKIP_PATTERNS = {"__pycache__", ".pyc", ".pyo", ".DS_Store", "Thumbs.db", ".git"}

# 工具探测列表
DETECT_TOOLS = [
    "cmake",
    "ninja",
    "make",
    "gcc",
    "g++",
    "openocd",
    "arm-none-eabi-gcc",
    "arm-none-eabi-gdb",
    "aarch64-none-linux-gnu-gcc",
    "aarch64-linux-gnu-gcc",
    "gdb-multiarch",
    "platformio",
    "pio",
    "idf.py",
    "JLinkExe",
    "JLinkGDBServerCLExe",
    "cppcheck",
    "clang-tidy",
]


def _should_skip(path: Path) -> bool:
    """判断是否应该跳过文件。"""
    for part in path.parts:
        if part in SKIP_PATTERNS or part.endswith((".pyc", ".pyo")):
            return True
    return False


def _git_short_hash() -> str:
    """获取 Git 短哈希。"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except FileNotFoundError:
        pass
    return "unknown"


def _copy_tree(src: Path, dst: Path, force: bool = False) -> tuple[int, int]:
    """递归拷贝目录，返回 (copied, skipped) 计数。"""
    copied = 0
    skipped = 0
    
    if not src.exists():
        return copied, skipped
    
    for item in src.rglob("*"):
        if not item.is_file():
            continue
        rel = item.relative_to(src)
        if _should_skip(rel):
            continue
        target = dst / rel
        if target.exists() and not force:
            skipped += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
        copied += 1
    return copied, skipped


def _available_skills() -> list[str]:
    """获取可用技能列表。"""
    if not SKILLS_SRC.is_dir():
        return []
    skills = []
    # 遍历分类目录
    for category_dir in SKILLS_SRC.iterdir():
        if category_dir.is_dir():
            # 在分类目录下查找技能
            for skill_dir in category_dir.iterdir():
                if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                    skills.append(f"{category_dir.name}/{skill_dir.name}")
    return sorted(skills)


def _read_skill_description(skill_name: str) -> str:
    """读取技能描述。"""
    # 支持 category/skill-name 格式
    if "/" in skill_name:
        parts = skill_name.split("/")
        if len(parts) == 2:
            skill_md = SKILLS_SRC / parts[0] / parts[1] / "SKILL.md"
        else:
            return ""
    else:
        # 尝试在所有分类目录中查找
        skill_md = None
        for category_dir in SKILLS_SRC.iterdir():
            if category_dir.is_dir():
                candidate = category_dir / skill_name / "SKILL.md"
                if candidate.is_file():
                    skill_md = candidate
                    break
        if skill_md is None:
            return ""
    if not skill_md.is_file():
        return ""
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError:
        return ""
    
    # 解析 YAML front matter
    m = re.search(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return ""
    for line in m.group(1).splitlines():
        line = line.strip()
        if line.startswith("description:"):
            desc = line[len("description:"):].strip()
            return desc.strip("\"'")
    return ""


def _skills_dir(project: Path, agent_type: str = ".claude") -> Path:
    """获取技能的安装目录。"""
    return project / agent_type / "skills"


def _meta_path(project: Path, agent_type: str = ".claude") -> Path:
    """获取元数据文件路径。"""
    return _skills_dir(project, agent_type) / META_FILENAME


def _load_meta(project: Path, agent_type: str = ".claude") -> dict:
    """加载安装元数据。"""
    mp = _meta_path(project, agent_type)
    if mp.is_file():
        try:
            return json.loads(mp.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_meta(project: Path, meta: dict, agent_type: str = ".claude") -> None:
    """保存安装元数据。"""
    skills_dir = _skills_dir(project, agent_type)
    skills_dir.mkdir(parents=True, exist_ok=True)
    mp = _meta_path(project, agent_type)
    mp.write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _load_tool_config(project: Path) -> dict:
    """加载工具配置。"""
    config_path = project / TOOL_CONFIG_FILENAME
    if config_path.is_file():
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_tool_config(project: Path, config: dict) -> None:
    """保存工具配置。"""
    config_path = project / TOOL_CONFIG_FILENAME
    config_path.write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


# ── 命令实现 ────────────────────────────────────────────────────────


def cmd_list() -> None:
    """列出可用技能。"""
    skills = _available_skills()
    if not skills:
        print("未找到可用技能。")
        return
    print(f"可用技能（共 {len(skills)} 个）：\n")
    max_name = max(len(s) for s in skills)
    for s in skills:
        desc = _read_skill_description(s)
        print(f"  {s:<{max_name}}  {desc}")


def _check_os_environment() -> tuple[str, str]:
    """检查操作系统环境。"""
    if sys.platform.startswith("win"):
        return "windows", "Windows"
    elif sys.platform.startswith("linux"):
        return "linux", "Linux"
    elif sys.platform.startswith("darwin"):
        return "darwin", "macOS"
    else:
        return sys.platform, "Unknown"


def _check_writable(path: Path) -> bool:
    """检查目录是否可写。"""
    try:
        # 创建测试文件
        test_file = path / ".test_write.tmp"
        test_file.write_text("test", encoding="utf-8")
        test_file.unlink()
        return True
    except OSError:
        return False


def _check_skill_exists_in_registry(project: Path, skill_name: str, agent_type: str) -> bool:
    """检查技能是否已在注册表中存在。"""
    registry_path = _skills_dir(project, agent_type) / "shared" / "skill_registry.yaml"
    if not registry_path.is_file():
        return False
    
    try:
        content = registry_path.read_text(encoding="utf-8")
        return f"name: {skill_name}" in content
    except OSError:
        return False


def _check_skill_files(skill_path: Path) -> list[str]:
    """检查技能文件完整性，返回缺失的文件列表。"""
    required_files = ["SKILL.md"]
    missing = []
    
    for required in required_files:
        if not (skill_path / required).is_file():
            missing.append(required)
    
    return missing


def cmd_install(
    project: Path,
    skill_names: list[str] | None,
    force: bool,
    agent_type: str,
) -> None:
    """安装技能到目标项目。"""
    print("🔧 开始技能安装流程...\n")
    
    # 步骤 1：检查源技能文件完整性
    print("步骤 1/7：检查源技能文件完整性")
    available = _available_skills()
    if not available:
        print("   ❌ 错误：未在仓库中找到任何技能。")
        sys.exit(1)
    print(f"   ✓ 找到 {len(available)} 个可用技能")

    # 解析技能名称（支持 category/skill 格式）
    to_install = []
    for name in (skill_names or []):
        # 支持 "software/build-linux-app" 格式
        if "/" in name:
            parts = name.split("/")
            if len(parts) == 2:
                skill_path = SKILLS_SRC / parts[0] / parts[1]
                missing = _check_skill_files(skill_path)
                if missing:
                    print(f"   ❌ 技能 {name} 文件不完整，缺失: {', '.join(missing)}")
                    sys.exit(1)
                if (skill_path / "SKILL.md").exists():
                    to_install.append({"name": parts[1], "category": parts[0], "path": skill_path})
                else:
                    print(f"   ❌ 技能不存在：{name}")
                    sys.exit(1)
            else:
                print(f"   ❌ 无效的技能名称格式：{name}")
                sys.exit(1)
        else:
            # 尝试在所有分类目录中查找
            found = False
            for category_dir in SKILLS_SRC.iterdir():
                if category_dir.is_dir():
                    skill_path = category_dir / name
                    if (skill_path / "SKILL.md").exists():
                        missing = _check_skill_files(skill_path)
                        if missing:
                            print(f"   ❌ 技能 {name} 文件不完整，缺失: {', '.join(missing)}")
                            sys.exit(1)
                        to_install.append({"name": name, "category": category_dir.name, "path": skill_path})
                        found = True
                        break
            if not found:
                print(f"   ❌ 技能不存在：{name}")
                print(f"   可用技能：{', '.join(available)}")
                sys.exit(1)

    # 如果未指定技能，安装全部
    if not to_install:
        for skill_full_name in available:
            parts = skill_full_name.split("/")
            if len(parts) == 2:
                skill_path = SKILLS_SRC / parts[0] / parts[1]
                to_install.append({"name": parts[1], "category": parts[0], "path": skill_path})

    # 步骤 2：检查目标项目位置和环境
    print("\n步骤 2/7：检查目标项目位置和环境")
    os_code, os_name = _check_os_environment()
    print(f"   ✓ 操作系统：{os_name} ({os_code})")
    print(f"   ✓ 目标项目：{project}")
    
    # 步骤 3：检查目标目录可写性和权限
    print("\n步骤 3/7：检查目标目录可写性")
    dest = _skills_dir(project, agent_type)
    dest_parent = dest.parent
    
    if not dest_parent.exists():
        try:
            dest_parent.mkdir(parents=True, exist_ok=True)
            print(f"   ✓ 创建目录：{dest_parent}")
        except OSError as e:
            print(f"   ❌ 无法创建目录 {dest_parent}: {e}")
            sys.exit(1)
    
    if _check_writable(dest_parent):
        print(f"   ✓ 目录可写：{dest_parent}")
    else:
        print(f"   ❌ 目录不可写：{dest_parent}")
        sys.exit(1)

    # 步骤 4：检查技能是否已存在（冲突检测）
    print("\n步骤 4/7：检查技能是否已存在（冲突检测）")
    existing_skills = []
    for skill in to_install:
        skill_name = skill["name"]
        # 检查目录是否存在
        if (dest / skill_name).is_dir():
            if force:
                print(f"   ⚠️ 技能 {skill_name} 已存在，将强制覆盖")
            else:
                existing_skills.append(skill_name)
        
        # 检查注册表
        if _check_skill_exists_in_registry(project, skill_name, agent_type):
            print(f"   ⚠️ 技能 {skill_name} 已在注册表中")
    
    if existing_skills and not force:
        print(f"   ❌ 以下技能已存在：{', '.join(existing_skills)}")
        print("   使用 --force 参数强制覆盖")
        sys.exit(1)

    # 步骤 5：复制技能文件到目标项目
    print("\n步骤 5/7：复制技能文件到目标项目")
    total_copied = 0
    total_skipped = 0
    failed = []

    # 拷贝技能目录
    for skill in to_install:
        skill_name = skill["name"]
        skill_path = skill["path"]
        
        dst = dest / skill_name
        c, s = _copy_tree(skill_path, dst, force)
        total_copied += c
        total_skipped += s
        
        # 确保 SKILL.md 存在
        skill_md = dst / "SKILL.md"
        if not skill_md.is_file():
            print(f"   ⚠️ 警告：SKILL.md 不存在，创建默认文件")
            skill_md.write_text(f"---\nname: {skill_name}\ndescription: '未定义描述'\nversion: '1.0.0'\n---\n\n# {skill_name}\n\n此技能尚未添加详细描述。\n", encoding="utf-8")
            total_copied += 1
        
        status = "✓" if c > 0 else ("跳过" if s > 0 else "空")
        print(f"   {status} {skill['category']}/{skill_name} ({c} 文件)")

    # 拷贝 shared 目录
    if SHARED_SRC.is_dir():
        c, s = _copy_tree(SHARED_SRC, dest / "shared", force)
        total_copied += c
        total_skipped += s
        print(f"   {'✓' if c > 0 else '跳过'} shared ({c} 文件)")

    # 拷贝 agents 目录（如果存在且需要）
    if AGENTS_SRC.exists():
        agents_dest = _skills_dir(project, agent_type) / "shared"
        agents_dest.mkdir(parents=True, exist_ok=True)
        # 拷贝共享的 agents 配置
        for agent_file in AGENTS_SRC.glob("*.yaml"):
            if agent_file.name == "template.yaml":
                continue  # 不拷贝模板
            target = agents_dest / agent_file.name
            if not target.exists() or force:
                shutil.copy2(agent_file, target)
                print(f"   ✓ agents/{agent_file.name}")
                total_copied += 1

    # 拷贝 rules 目录（安全规则）
    rules_dest = dest.parent / "rules"
    if RULES_SRC.is_dir():
        c, s = _copy_tree(RULES_SRC, rules_dest, force)
        total_copied += c
        total_skipped += s
        print(f"   {'✓' if c > 0 else '跳过'} rules ({c} 文件)")
    
    # 拷贝 design_planning.md（设计规划文档）
    if DESIGN_PLANNING_SRC.is_file():
        design_planning_dest = dest.parent / "design_planning.md"
        if not design_planning_dest.exists() or force:
            shutil.copy2(DESIGN_PLANNING_SRC, design_planning_dest)
            print(f"   ✓ design_planning.md")
            total_copied += 1

    # 步骤 6：更新技能注册表
    print("\n步骤 6/7：更新技能注册表")
    meta = _load_meta(project, agent_type)
    existing_skill_names = set(meta.get("skills", []))
    new_skill_names = [s["name"] for s in to_install]
    existing_skill_names.update(new_skill_names)
    
    meta.update(
        {
            "source": "plumb-link",
            "version": _git_short_hash(),
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "skills": sorted(existing_skill_names),
            "os": os_code,
        }
    )
    _save_meta(project, meta, agent_type)
    print(f"   ✓ 更新注册表，共 {len(existing_skill_names)} 个技能")

    # 创建项目根 SKILL.md
    print("\n创建项目根 SKILL.md")
    project_skill_md = project / "SKILL.md"
    if not project_skill_md.exists() or force:
        # 按分类整理技能
        skills_by_category = {}
        for skill in to_install:
            category = skill["category"]
            if category not in skills_by_category:
                skills_by_category[category] = []
            skills_by_category[category].append(skill["name"])
        
        # 生成 SKILL.md 内容
        skill_md_content = f"""---
name: {project.name}
description: "项目技能使用指南"
version: "1.0.0"
---

# {project.name} 技能使用指南

## 项目概述
本项目使用 Plumb-Link 技能体系进行开发。

## 已安装技能

### 软件技能
"""
        for skill_name in sorted(skills_by_category.get("software", [])):
            skill_desc = _read_skill_description(f"software/{skill_name}")
            skill_md_content += f"- `{skill_name}`: {skill_desc}\n"
        
        skill_md_content += "\n### 硬件技能\n"
        for skill_name in sorted(skills_by_category.get("hardware", [])):
            skill_desc = _read_skill_description(f"hardware/{skill_name}")
            skill_md_content += f"- `{skill_name}`: {skill_desc}\n"
        
        skill_md_content += "\n### 平台技能\n"
        for skill_name in sorted(skills_by_category.get("platform", [])):
            skill_desc = _read_skill_description(f"platform/{skill_name}")
            skill_md_content += f"- `{skill_name}`: {skill_desc}\n"
        
        skill_md_content += "\n### 工作流技能\n"
        for skill_name in sorted(skills_by_category.get("workflow", [])):
            skill_desc = _read_skill_description(f"workflow/{skill_name}")
            skill_md_content += f"- `{skill_name}`: {skill_desc}\n"
        
        skill_md_content += """
## 使用规范

### 1. 技能激活
涉及敏感操作的技能需要用户手动激活：
- 查看 `.trae/skills/[skill-name]/CONFIG.md`
- 修改 `config.json` 中的 `security.enabled = true`

### 2. 安全约束
所有操作必须遵守 `.trae/rules/99-security-redline.md` 中的安全红线

### 3. 技能调用
大模型应优先使用已安装的技能，避免绕过技能直接执行命令

## 技能注册表
查看 `.trae/skills/shared/skill_registry.yaml` 获取完整技能列表

## 配置文件
- `.trae/settings.json`: 项目全局配置
- `.trae/skills/[skill-name]/config.json`: 技能配置

## 设计规范
查看 `.trae/design_planning.md` 了解技能体系设计规范
"""
        
        project_skill_md.write_text(skill_md_content, encoding="utf-8")
        print(f"   ✓ 创建项目根 SKILL.md: {project_skill_md}")
        total_copied += 1

    # 步骤 7：验证加载结果
    print("\n步骤 7/7：验证加载结果")
    success = True
    
    # 验证目录创建
    if not dest.is_dir():
        print("   ❌ 技能目录未创建")
        success = False
    else:
        print(f"   ✓ 技能目录：{dest}")
    
    # 验证 meta 文件
    meta_path = _meta_path(project, agent_type)
    if not meta_path.is_file():
        print("   ❌ 元数据文件未创建")
        success = False
    else:
        print(f"   ✓ 元数据文件：{meta_path}")
    
    # 验证技能文件
    for skill in to_install:
        skill_dst = dest / skill["name"]
        skill_md = skill_dst / "SKILL.md"
        if skill_dst.is_dir() and skill_md.is_file():
            print(f"   ✓ 技能 {skill['name']} 已安装")
        else:
            print(f"   ❌ 技能 {skill['name']} 安装不完整")
            success = False

    # 打印结果
    print(f"\n{'✓' if success else '✗'} 安装完成：{total_copied} 文件已拷贝，{total_skipped} 文件已跳过。")
    print(f"目标目录：{dest}")
    
    if failed:
        print(f"\n警告：以下技能安装失败：{', '.join(failed)}")
    
    if total_skipped > 0 and not force:
        print("提示：使用 --force 可覆盖已有文件。")


def cmd_remove(project: Path, skill_names: list[str], agent_type: str) -> None:
    """删除指定的已安装技能。"""
    dest = _skills_dir(project, agent_type)
    meta = _load_meta(project, agent_type)

    if not meta:
        print("错误：未找到安装记录。无法执行删除操作。", file=sys.stderr)
        return

    installed_skills = set(meta.get("skills", []))
    
    # 验证要删除的技能是否已安装
    valid_skills = []
    invalid_skills = []
    for name in skill_names:
        # 支持 category/skill-name 格式，提取技能名
        skill_name = name.split("/")[-1]  # 取最后一部分作为技能名
        if skill_name in installed_skills:
            valid_skills.append(skill_name)
        else:
            invalid_skills.append(name)
    
    if invalid_skills:
        print(f"警告：以下技能未安装或不存在：{', '.join(invalid_skills)}", file=sys.stderr)
    
    if not valid_skills:
        print("没有可删除的技能。")
        return

    # 执行删除
    removed = 0
    for skill in valid_skills:
        skill_dir = dest / skill
        if skill_dir.is_dir():
            shutil.rmtree(skill_dir)
            print(f"  ✓ 已删除 {skill}")
            removed += 1
        else:
            print(f"  ✗ {skill} (目录不存在)")

    # 更新 meta 文件
    remaining_skills = installed_skills - set(valid_skills)
    meta["skills"] = sorted(remaining_skills)
    _save_meta(project, meta, agent_type)

    print(f"\n删除完成：已成功删除 {removed} 个技能。")

    # 如果没有剩余技能，清理目录
    if not remaining_skills:
        # 删除 shared
        shared_dir = dest / "shared"
        if shared_dir.is_dir():
            shutil.rmtree(shared_dir)
            print("  ✓ 已删除 shared")
        
        # 删除 meta 文件
        mp = _meta_path(project, agent_type)
        if mp.is_file():
            mp.unlink()
        
        # 如果 skills 目录为空，也删除
        if dest.is_dir() and not any(dest.iterdir()):
            dest.rmdir()
            # 尝试删除 .claude 或 .trae 目录
            agent_dir = project / agent_type
            if agent_dir.is_dir() and not any(agent_dir.iterdir()):
                agent_dir.rmdir()


def cmd_uninstall(project: Path, agent_type: str) -> None:
    """卸载已安装的技能。"""
    dest = _skills_dir(project, agent_type)
    meta = _load_meta(project, agent_type)

    if not meta:
        # 没有 meta 文件，尝试列出疑似目录
        if dest.is_dir():
            dirs = [d.name for d in dest.iterdir() if d.is_dir()]
            if dirs:
                print("未找到安装记录，但发现以下目录：")
                for d in sorted(dirs):
                    print(f"  - {d}")
                print("请手动确认并删除。")
                return
        print("未找到安装记录，也没有发现已安装的技能。")
        return

    skills = meta.get("skills", [])
    removed = 0

    for skill in skills:
        skill_dir = dest / skill
        if skill_dir.is_dir():
            shutil.rmtree(skill_dir)
            print(f"  ✓ 已删除 {skill}")
            removed += 1

    # 删除 shared
    shared_dir = dest / "shared"
    if shared_dir.is_dir():
        shutil.rmtree(shared_dir)
        print("  ✓ 已删除 shared")

    # 删除 meta 文件
    mp = _meta_path(project, agent_type)
    if mp.is_file():
        mp.unlink()

    # 如果 skills 目录为空，也删除
    if dest.is_dir() and not any(dest.iterdir()):
        dest.rmdir()
        # 尝试删除 .claude 或 .trae 目录
        agent_dir = project / agent_type
        if agent_dir.is_dir() and not any(agent_dir.iterdir()):
            agent_dir.rmdir()

    print(f"\n卸载完成：已删除 {removed} 个技能。")


def cmd_status(project: Path, agent_type: str) -> None:
    """显示当前安装状态。"""
    meta = _load_meta(project, agent_type)
    if not meta:
        print("未找到安装记录。该项目可能尚未安装 plumb-link 技能。")
        return

    print("Plumb-Link 安装状态：\n")
    print(f"  版本：     {meta.get('version', '未知')}")
    print(f"  安装时间： {meta.get('installed_at', '未知')}")
    print(f"  来源：     {meta.get('source', '未知')}")

    skills = meta.get("skills", [])
    dest = _skills_dir(project, agent_type)
    print(f"\n  已安装技能（{len(skills)} 个）：")
    for s in skills:
        exists = (dest / s).is_dir()
        marker = "✓" if exists else "✗ (目录缺失)"
        print(f"    {marker} {s}")

    # 显示工具路径配置
    config = _load_tool_config(project)
    tools = config.get("tools", {})
    if tools:
        print(f"\n  工具路径配置（{len(tools)} 个）：")
        for name, path in sorted(tools.items()):
            print(f"    {name}: {path}")


def cmd_detect(project: Path) -> None:
    """探测工具路径。"""
    print("探测工具路径...\n")

    found = {}
    for tool in DETECT_TOOLS:
        path = shutil.which(tool)
        if path:
            found[tool] = path
            print(f"  ✓ {tool}: {path}")
        else:
            print(f"  ✗ {tool}: 未找到")

    if not found:
        print("\n未找到任何工具，请确认工具已安装并在 PATH 中。")
        return

    # 写入配置
    config = _load_tool_config(project)
    tools = config.setdefault("tools", {})
    tools.update(found)
    _save_tool_config(project, config)

    print(f"\n已将 {len(found)} 个工具路径写入 {project / TOOL_CONFIG_FILENAME}")


# ── CLI 主函数 ────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Plumb-Link 技能安装器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "project",
        nargs="?",
        help="目标工程路径",
    )
    parser.add_argument(
        "--skills",
        nargs="+",
        metavar="SKILL",
        help="只安装指定技能（默认安装全部）",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制覆盖已有文件",
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="卸载已安装的技能",
    )
    parser.add_argument(
        "--remove",
        nargs="+",
        metavar="SKILL",
        help="删除指定的已安装技能（支持多个技能）",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_skills",
        help="列出仓库中所有可用技能",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="显示当前安装状态",
    )
    parser.add_argument(
        "--detect",
        action="store_true",
        help="安装后自动探测工具路径",
    )
    parser.add_argument(
        "--agent",
        type=str,
        default=".claude",
        choices=[".claude", ".trae"],
        help="目标 Agent 类型（默认 .claude）",
    )

    args = parser.parse_args()

    # --list 不需要 project 参数
    if args.list_skills:
        cmd_list()
        return

    if not args.project:
        parser.error("请指定目标工程路径（或使用 --list 查看可用技能）。")

    project = Path(args.project).resolve()
    if not project.is_dir():
        print(f"错误：目录不存在：{project}", file=sys.stderr)
        sys.exit(1)

    if args.uninstall:
        cmd_uninstall(project, args.agent)
        return

    if args.remove:
        cmd_remove(project, args.remove, args.agent)
        return

    if args.status:
        cmd_status(project, args.agent)
        return

    # 默认动作：安装
    cmd_install(project, args.skills, args.force, args.agent)

    if args.detect:
        print()
        cmd_detect(project)


if __name__ == "__main__":
    main()
