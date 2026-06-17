"""工具链环境检测与管理模块。

提供跨平台的编译工具链检测能力，支持本地编译和交叉编译。
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tool_config import get_tool_path


@dataclass
class ToolInfo:
    """工具信息。"""
    name: str
    path: str
    available: bool
    version: str | None = None
    source: str = "path"


@dataclass
class ToolchainEnv:
    """工具链环境快照。"""
    host_os: str
    tools: dict[str, ToolInfo]
    cross_compile: str | None = None


# 常用工具列表
COMMON_TOOLS = [
    # 主机编译器
    ("gcc", "gcc", ["--version"]),
    ("g++", "g++", ["--version"]),
    # 构建工具
    ("make", "make", ["--version"]),
    ("cmake", "cmake", ["--version"]),
    ("ninja", "ninja", ["--version"]),
    # 交叉编译工具链
    ("arm-none-eabi-gcc", "arm-none-eabi-gcc", ["--version"]),
    ("arm-none-eabi-g++", "arm-none-eabi-g++", ["--version"]),
    ("aarch64-linux-gnu-gcc", "aarch64-linux-gnu-gcc", ["--version"]),
    ("aarch64-linux-gnu-g++", "aarch64-linux-gnu-g++", ["--version"]),
    # 调试工具
    ("gdb", "gdb", ["--version"]),
    ("arm-none-eabi-gdb", "arm-none-eabi-gdb", ["--version"]),
    ("gdb-multiarch", "gdb-multiarch", ["--version"]),
    # 静态分析工具
    ("cppcheck", "cppcheck", ["--version"]),
    ("clang-tidy", "clang-tidy", ["--version"]),
]


def _detect_os() -> str:
    """检测当前操作系统。"""
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    if system == "windows":
        return "windows"
    return "linux"


def _probe_version(cmd: list[str]) -> str | None:
    """探测工具版本。"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            env={k: v for k, v in os.environ.items() if not k.startswith("PYTHON")},
        )
        if result.returncode == 0:
            lines = result.stdout.strip().splitlines()
            if lines:
                return lines[0].strip()
    except Exception:
        pass
    return None


def detect_tool(tool_name: str, cmd_args: list[str], workspace: Path | None = None) -> ToolInfo:
    """检测单个工具。"""
    # 1. 先检查配置文件
    config_path = get_tool_path(tool_name, workspace)
    if config_path:
        if Path(config_path).exists():
            version = _probe_version([config_path] + cmd_args)
            return ToolInfo(
                name=tool_name,
                path=config_path,
                available=True,
                version=version,
                source="config"
            )
    
    # 2. 检查环境变量
    env_path = os.environ.get(f"{tool_name.upper()}_PATH")
    if env_path and Path(env_path).exists():
        version = _probe_version([env_path] + cmd_args)
        return ToolInfo(
            name=tool_name,
            path=env_path,
            available=True,
            version=version,
            source="env"
        )
    
    # 3. 检查 PATH
    path_in_path = shutil.which(tool_name)
    if path_in_path:
        version = _probe_version([path_in_path] + cmd_args)
        return ToolInfo(
            name=tool_name,
            path=path_in_path,
            available=True,
            version=version,
            source="path"
        )
    
    # 4. 检查 Windows 特定路径（MinGW/Cygwin）
    if platform.system() == "Windows":
        common_paths = [
            "C:\\msys64\\mingw64\\bin",
            "C:\\msys64\\mingw32\\bin",
            "C:\\MinGW\\bin",
            "C:\\MinGW64\\bin",
            os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "mingw-w64", "x86_64-8.1.0-posix-seh-rt_v6-rev0", "mingw64", "bin"),
        ]
        for base_path in common_paths:
            tool_path = os.path.join(base_path, f"{tool_name}.exe")
            if os.path.exists(tool_path):
                version = _probe_version([tool_path] + cmd_args)
                return ToolInfo(
                    name=tool_name,
                    path=tool_path,
                    available=True,
                    version=version,
                    source="path"
                )
    
    return ToolInfo(
        name=tool_name,
        path="",
        available=False,
        version=None,
        source="not_found"
    )


def detect_toolchain(workspace: Path | None = None) -> ToolchainEnv:
    """检测完整的工具链环境。"""
    host_os = _detect_os()
    tools: dict[str, ToolInfo] = {}
    
    for tool_name, cmd_name, version_args in COMMON_TOOLS:
        tools[tool_name] = detect_tool(cmd_name, version_args, workspace)
    
    # 检测交叉编译前缀
    cross_compile = None
    if tools.get("aarch64-linux-gnu-gcc") and tools["aarch64-linux-gnu-gcc"].available:
        cross_compile = "aarch64-linux-gnu-"
    elif tools.get("arm-none-eabi-gcc") and tools["arm-none-eabi-gcc"].available:
        cross_compile = "arm-none-eabi-"
    
    return ToolchainEnv(
        host_os=host_os,
        tools=tools,
        cross_compile=cross_compile
    )


def get_tool_path_or_default(
    tool_name: str,
    workspace: Path | None = None,
    default: str = ""
) -> str:
    """获取工具路径，不存在时返回默认值。"""
    # 1. 配置文件
    config_path = get_tool_path(tool_name, workspace)
    if config_path and Path(config_path).exists():
        return config_path
    
    # 2. 环境变量
    env_path = os.environ.get(f"{tool_name.upper()}_PATH")
    if env_path and Path(env_path).exists():
        return env_path
    
    # 3. PATH
    path_in_path = shutil.which(tool_name)
    if path_in_path:
        return path_in_path
    
    # 4. Windows 特定路径
    if platform.system() == "Windows":
        tool_exe = f"{tool_name}.exe"
        common_paths = [
            "C:\\msys64\\mingw64\\bin",
            "C:\\msys64\\mingw32\\bin",
            "C:\\MinGW\\bin",
            "C:\\MinGW64\\bin",
        ]
        for base_path in common_paths:
            tool_path = os.path.join(base_path, tool_exe)
            if os.path.exists(tool_path):
                return tool_path
    
    return default


def validate_toolchain(required_tools: list[str], workspace: Path | None = None) -> tuple[bool, list[str]]:
    """验证必需工具是否可用。"""
    missing = []
    env = detect_toolchain(workspace)
    
    for tool in required_tools:
        tool_info = env.tools.get(tool)
        if not tool_info or not tool_info.available:
            missing.append(tool)
    
    return (len(missing) == 0, missing)


def format_toolchain_report(env: ToolchainEnv) -> str:
    """格式化工具链检测报告。"""
    lines = [
        f"操作系统: {env.host_os}",
        "",
        "已检测工具:",
    ]
    
    for tool_name, info in sorted(env.tools.items()):
        status = "[OK]" if info.available else "[--]"
        source = f" [{info.source}]" if info.source != "path" else ""
        version = f" | {info.version[:50]}..." if info.version and len(info.version) > 50 else f" | {info.version}" if info.version else ""
        lines.append(f"  {status} {tool_name}: {info.path or '未找到'}{source}{version}")
    
    if env.cross_compile:
        lines.append(f"\n交叉编译前缀: {env.cross_compile}")
    
    return "\n".join(lines)


def env_to_dict(env: ToolchainEnv) -> dict[str, Any]:
    """将 ToolchainEnv 转换为字典格式，便于序列化。"""
    tools_dict = {}
    for name, info in env.tools.items():
        tools_dict[name] = {
            "available": info.available,
            "path": info.path,
            "version": info.version,
            "source": info.source,
        }
    
    return {
        "host_os": env.host_os,
        "cross_compile": env.cross_compile,
        "tools": tools_dict,
    }


def save_env_settings(env: ToolchainEnv, project_dir: Path) -> Path:
    """保存工具链环境配置到项目目录（合并到现有配置）。"""
    settings_path = project_dir / ".trae" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 如果已有设置，合并工具链信息
    if settings_path.is_file():
        try:
            existing = json.loads(settings_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = {}
    else:
        existing = {}
    
    # 合并工具链信息
    existing["toolchain"] = env_to_dict(env)
    existing["toolchain_detected_at"] = datetime.now(timezone.utc).isoformat()
    
    settings_path.write_text(
        json.dumps(existing, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )
    
    return settings_path


def load_env_settings(project_dir: Path) -> dict[str, Any] | None:
    """从项目目录加载工具链环境配置。"""
    settings_path = project_dir / ".trae" / "settings.json"
    if not settings_path.is_file():
        return None
    
    try:
        return json.loads(settings_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
