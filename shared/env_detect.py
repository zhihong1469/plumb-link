"""统一环境探测入口。

提供一站式的项目和工具链环境探测，将结果保存到 .trae/settings.json。
"""

from __future__ import annotations

import sys
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from project_detect import detect_project, save_project_settings
from toolchain_env import detect_toolchain, save_env_settings


def detect_and_save(project_dir: Path | str) -> dict[str, Any]:
    """执行完整的环境探测并保存到 settings.json。"""
    if isinstance(project_dir, str):
        project_dir = Path(project_dir).resolve()
    
    # 探测工具链环境
    toolchain_env = detect_toolchain()
    save_env_settings(toolchain_env, project_dir)
    
    # 探测项目信息
    project_info = detect_project(project_dir)
    save_project_settings(project_info, project_dir)
    
    # 返回合并后的结果
    return {
        "toolchain": {
            "host_os": toolchain_env.host_os,
            "cross_compile": toolchain_env.cross_compile,
            "detected_at": "recent",
        },
        "project": project_info,
    }


def format_settings_for_llm(settings: dict[str, Any]) -> str:
    """将设置信息格式化为大模型友好的文本格式。"""
    lines = []
    
    # 工具链信息
    if "toolchain" in settings:
        tc = settings["toolchain"]
        lines.append("## 工具链环境")
        lines.append(f"- 操作系统: {tc.get('host_os', '未知')}")
        lines.append(f"- 交叉编译前缀: {tc.get('cross_compile', '无')}")
        lines.append(f"- 检测时间: {tc.get('toolchain_detected_at', '未知')}")
        lines.append("")
        lines.append("### 可用工具:")
        tools = tc.get("tools", {})
        for name, info in sorted(tools.items()):
            if info.get("available"):
                lines.append(f"  - {name}: {info.get('path', '')}")
    
    # 项目信息
    if "project" in settings:
        p = settings["project"]
        lines.append("")
        lines.append("## 项目信息")
        lines.append(f"- 工作区: {p.get('workspace_root', '未知')}")
        lines.append(f"- 构建系统: {p.get('build_system', '未知')}")
        lines.append(f"- 目标平台: {p.get('target_platform', '未知')}")
        lines.append(f"- 目标 MCU: {p.get('target_mcu', '未知')}")
        lines.append(f"- RTOS: {p.get('rtos', '未知')}")
        lines.append(f"- 调试探针: {', '.join(p.get('probes', []))}")
        lines.append(f"- 检测时间: {p.get('project_detected_at', '未知')}")
    
    return "\n".join(lines)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="统一环境探测工具")
    parser.add_argument(
        "project_dir",
        nargs="?",
        default=".",
        help="目标项目目录（默认当前目录）"
    )
    parser.add_argument(
        "--format",
        choices=["json", "llm"],
        default="json",
        help="输出格式"
    )
    
    args = parser.parse_args()
    
    project_dir = Path(args.project_dir).resolve()
    
    # 执行探测并保存
    result = detect_and_save(project_dir)
    
    # 输出结果
    if args.format == "llm":
        from project_detect import load_project_settings
        settings = load_project_settings(project_dir) or result
        print(format_settings_for_llm(settings))
    else:
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    print(f"\n配置已保存到: {project_dir / '.trae' / 'settings.json'}")


if __name__ == "__main__":
    main()
