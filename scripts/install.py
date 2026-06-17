#!/usr/bin/env python3
"""Plumb-Link 技能安装器。

将技能从 plumb-link 安装到目标软件工程项目。

用法：
    python scripts/install.py /path/to/project                      # 安装全部技能
    python scripts/install.py /path/to/project --skills build-linux-app gpio-config
    python scripts/install.py /path/to/project --force              # 强制覆盖
    python scripts/install.py /path/to/project --detect            # 安装后探测工具路径
    python scripts/install.py /path/to/project --uninstall          # 卸载
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


def cmd_install(
    project: Path,
    skill_names: list[str] | None,
    force: bool,
    agent_type: str,
) -> None:
    """安装技能到目标项目。"""
    available = _available_skills()
    if not available:
        print("错误：未在仓库中找到任何技能。", file=sys.stderr)
        sys.exit(1)

    # 解析技能名称（支持 category/skill 格式）
    to_install = []
    for name in (skill_names or []):
        # 支持 "software/build-linux-app" 格式
        if "/" in name:
            parts = name.split("/")
            if len(parts) == 2:
                skill_path = SKILLS_SRC / parts[0] / parts[1]
                if (skill_path / "SKILL.md").exists():
                    to_install.append(parts[1])  # 只保存技能名
                else:
                    print(f"错误：技能不存在：{name}", file=sys.stderr)
                    sys.exit(1)
            else:
                print(f"错误：无效的技能名称格式：{name}", file=sys.stderr)
                sys.exit(1)
        else:
            if name not in available:
                print(f"错误：技能不存在：{name}", file=sys.stderr)
                print(f"可用技能：{', '.join(available)}", file=sys.stderr)
                sys.exit(1)
            to_install.append(name)

    # 如果未指定技能，安装全部
    if not to_install:
        to_install = available

    dest = _skills_dir(project, agent_type)
    dest.mkdir(parents=True, exist_ok=True)

    total_copied = 0
    total_skipped = 0
    failed = []

    # 拷贝技能目录
    for skill in to_install:
        # 查找技能目录
        skill_dir = None
        for category_dir in SKILLS_SRC.iterdir():
            if category_dir.is_dir():
                candidate = category_dir / skill
                if candidate.exists() and (candidate / "SKILL.md").exists():
                    skill_dir = candidate
                    break
        
        if not skill_dir:
            failed.append(skill)
            print(f"  ✗ {skill} (未找到)")
            continue
        
        dst = dest / skill
        c, s = _copy_tree(skill_dir, dst, force)
        total_copied += c
        total_skipped += s
        status = "✓" if c > 0 else ("跳过" if s > 0 else "空")
        print(f"  {status} {skill} ({c} 文件)")

    # 拷贝 shared 目录
    if SHARED_SRC.is_dir():
        c, s = _copy_tree(SHARED_SRC, dest / "shared", force)
        total_copied += c
        total_skipped += s
        print(f"  {'✓' if c > 0 else '跳过'} shared ({c} 文件)")

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
                print(f"  ✓ agents/{agent_file.name}")

    # 写入 meta
    meta = _load_meta(project, agent_type)
    existing_skills = set(meta.get("skills", []))
    existing_skills.update(to_install)
    meta.update(
        {
            "source": "plumb-link",
            "version": _git_short_hash(),
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "skills": sorted(existing_skills),
        }
    )
    _save_meta(project, meta, agent_type)

    # 打印结果
    print(f"\n安装完成：{total_copied} 文件已拷贝，{total_skipped} 文件已跳过。")
    print(f"目标目录：{dest}")
    
    if failed:
        print(f"\n警告：以下技能安装失败：{', '.join(failed)}")
    
    if total_skipped > 0 and not force:
        print("提示：使用 --force 可覆盖已有文件。")


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
