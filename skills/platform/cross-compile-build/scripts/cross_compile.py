#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交叉编译构建技能

功能：
1. 解压源码包
2. 自动检测构建系统（CMake/Makefile/Autotools/Cargo）
3. 执行交叉编译
4. 安装到指定位置

用法：
    python cross_compile.py --source <源码> --output <输出目录> --install <安装目录>
    python cross_compile.py -s source.tar.gz -o build -i /opt/install -t arm-linux-gnueabihf-

作者：Plumb-Link Team
版本：1.0.0
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class BuildSystem(Enum):
    """支持的构建系统"""
    CMAKE = "cmake"
    MAKEFILE = "makefile"
    AUTOTOOLS = "autotools"
    CARGO = "cargo"
    UNKNOWN = "unknown"


class BuildType(Enum):
    """构建类型"""
    DEBUG = "Debug"
    RELEASE = "Release"
    RELWITHDEBINFO = "RelWithDebInfo"
    MINSIZEREL = "MinSizeRel"


@dataclass
class Config:
    """技能配置"""
    toolchain_prefix: str = "arm-linux-gnueabihf-"
    toolchain_path: str = "/usr"
    parallel_jobs: int = 0
    default_build_type: str = "Release"
    default_cmake_flags: str = "-DCMAKE_BUILD_TYPE=Release"
    default_make_flags: str = ""
    default_install_prefix: str = "/usr/local"
    use_destdir: bool = True
    security_enabled: bool = False
    blocked_paths: list = field(default_factory=lambda: ["/etc", "/usr", "/bin"])
    log_level: str = "INFO"
    verbose: bool = False
    toolchain_presets: dict = field(default_factory=dict)


@dataclass
class BuildResult:
    """构建结果"""
    status: str
    summary: str
    source_path: str = ""
    build_system: str = ""
    output_dir: str = ""
    install_dir: str = ""
    toolchain: str = ""
    build_time: str = ""
    artifacts: list = field(default_factory=list)
    install_paths: list = field(default_factory=list)
    failure_category: str = ""
    error_code: str = ""
    error_message: str = ""
    suggestions: list = field(default_factory=list)


def load_config(config_path: Optional[str] = None) -> Config:
    """加载配置文件"""
    if config_path is None:
        script_dir = Path(__file__).parent
        config_path = script_dir / "config.json"

    config = Config()

    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if "toolchain" in data:
                config.toolchain_prefix = data["toolchain"].get("default_prefix", config.toolchain_prefix)
                config.toolchain_path = data["toolchain"].get("default_path", config.toolchain_path)

            if "build" in data:
                config.parallel_jobs = data["build"].get("parallel_jobs", config.parallel_jobs)
                config.default_build_type = data["build"].get("default_build_type", config.default_build_type)
                config.default_cmake_flags = data["build"].get("default_cmake_flags", config.default_cmake_flags)
                config.default_make_flags = data["build"].get("default_make_flags", config.default_make_flags)

            if "install" in data:
                config.default_install_prefix = data["install"].get("default_prefix", config.default_install_prefix)
                config.use_destdir = data["install"].get("use_destdir", config.use_destdir)

            if "security" in data:
                config.security_enabled = data["security"].get("enabled", config.security_enabled)
                config.blocked_paths = data["security"].get("blocked_paths", config.blocked_paths)

            if "toolchain_presets" in data:
                config.toolchain_presets = data["toolchain_presets"]

        except Exception as e:
            print(f"警告：加载配置文件失败: {e}", file=sys.stderr)

    return config


def run_command(cmd: list, cwd: str = None, env: dict = None, capture: bool = True) -> tuple:
    """执行命令"""
    if env is None:
        env = os.environ.copy()

    try:
        if capture:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=600
            )
        else:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                env=env,
                timeout=600
            )
            return result.returncode == 0, "", ""

        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "命令执行超时"
    except Exception as e:
        return False, "", str(e)


def detect_build_system(source_path: str) -> BuildSystem:
    """检测构建系统"""
    source_path = Path(source_path)

    # 如果是目录，直接检测
    if source_path.is_dir():
        check_dir = source_path
    else:
        # 解压到临时目录检测
        temp_dir = tempfile.mkdtemp()
        extract_archive(source_path, temp_dir)
        # 查找实际源码目录
        contents = list(Path(temp_dir).iterdir())
        if len(contents) == 1 and contents[0].is_dir():
            check_dir = contents[0]
        else:
            check_dir = Path(temp_dir)

    # 检测构建系统文件
    if (check_dir / "CMakeLists.txt").exists():
        return BuildSystem.CMAKE
    elif (check_dir / "Makefile").exists():
        return BuildSystem.MAKEFILE
    elif (check_dir / "configure.ac").exists() or (check_dir / "configure.in").exists():
        return BuildSystem.AUTOTOOLS
    elif (check_dir / "configure").exists() and (check_dir / "Makefile.in").exists():
        return BuildSystem.AUTOTOOLS
    elif (check_dir / "Cargo.toml").exists():
        return BuildSystem.CARGO
    elif (check_dir / "SConscript").exists():
        return BuildSystem.MAKEFILE  # SCons 使用 Makefile 风格
    else:
        # 进一步检测
        for makefile in ["GNUmakefile", "makefile"]:
            if (check_dir / makefile).exists():
                return BuildSystem.MAKEFILE

        return BuildSystem.UNKNOWN


def extract_archive(archive_path: str, output_dir: str) -> str:
    """解压压缩包"""
    archive_path = Path(archive_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    suffix = archive_path.suffix.lower()

    if suffix == ".zip":
        with zipfile.ZipFile(archive_path, "r") as zip_ref:
            zip_ref.extractall(output_dir)
    elif suffix in [".tar.gz", ".tgz"]:
        with tarfile.open(archive_path, "r:gz") as tar_ref:
            tar_ref.extractall(output_dir)
    elif suffix == ".tar.bz2":
        with tarfile.open(archive_path, "r:bz2") as tar_ref:
            tar_ref.extractall(output_dir)
    elif suffix == ".tar.xz":
        with tarfile.open(archive_path, "r:xz") as tar_ref:
            tar_ref.extractall(output_dir)
    elif suffix == ".tar":
        with tarfile.open(archive_path, "r:") as tar_ref:
            tar_ref.extractall(output_dir)
    else:
        raise ValueError(f"不支持的压缩格式: {suffix}")

    # 返回解压后的源码目录
    contents = list(output_dir.iterdir())
    if len(contents) == 1 and contents[0].is_dir():
        return str(contents[0])
    return str(output_dir)


def check_toolchain(toolchain_prefix: str, toolchain_path: str = "/usr") -> tuple:
    """检查工具链是否存在"""
    gcc_path = os.path.join(toolchain_path, "bin", f"{toolchain_prefix}gcc")

    if not os.path.exists(gcc_path):
        # 尝试在 PATH 中查找
        success, stdout, _ = run_command([f"{toolchain_prefix}gcc", "--version"])
        if success:
            return True, gcc_path

        return False, f"找不到工具链: {toolchain_prefix}gcc"

    return True, gcc_path


def create_cmake_toolchain_file(toolchain_prefix: str, toolchain_path: str, output_path: str):
    """创建 CMake 工具链文件"""
    content = f"""# CMake Toolchain File for Cross-Compilation
# Generated by cross-compile-build skill

set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR {"ARM" if "arm" in toolchain_prefix else "AARCH64" if "aarch64" in toolchain_prefix else "RISCV"})

# Specify the cross compiler
set(CMAKE_C_COMPILER   {toolchain_path}/bin/{toolchain_prefix}gcc)
set(CMAKE_CXX_COMPILER {toolchain_path}/bin/{toolchain_prefix}g++)
set(CMAKE_AR           {toolchain_path}/bin/{toolchain_prefix}ar CACHE FILEPATH "{toolchain_path}/bin/{toolchain_prefix}ar")
set(CMAKE_RANLIB       {toolchain_path}/bin/{toolchain_prefix}ranlib CACHE FILEPATH "{toolchain_path}/bin/{toolchain_prefix}ranlib")
set(CMAKE_LINKER       {toolchain_path}/bin/{toolchain_prefix}ld)

# Search for programs only in the build host directories
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)

# Search for libraries and headers only in the target directories
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)


def build_cmake(source_dir: str, build_dir: str, install_dir: str,
                toolchain_prefix: str, toolchain_path: str,
                cmake_flags: str, make_flags: str, parallel: int,
                build_type: str) -> tuple:
    """使用 CMake 构建"""
    os.makedirs(build_dir, exist_ok=True)

    # 创建工具链文件
    toolchain_file = os.path.join(build_dir, "toolchain.cmake")
    create_cmake_toolchain_file(toolchain_prefix, toolchain_path, toolchain_file)

    # 配置 CMake
    cmake_cmd = [
        "cmake",
        "-DCMAKE_TOOLCHAIN_FILE=" + toolchain_file,
        f"-DCMAKE_INSTALL_PREFIX={install_dir}",
        f"-DCMAKE_BUILD_TYPE={build_type}",
    ]

    if cmake_flags:
        cmake_cmd.extend(cmake_flags.split())

    cmake_cmd.append(source_dir)

    success, stdout, stderr = run_command(cmake_cmd, cwd=build_dir)
    if not success:
        return False, f"CMake 配置失败:\n{stdout}\n{stderr}"

    # 编译
    jobs = ["-j", str(parallel)] if parallel > 0 else []
    make_cmd = ["cmake", "--build", ".", "--config", build_type] + jobs

    success, stdout, stderr = run_command(make_cmd, cwd=build_dir)
    if not success:
        return False, f"CMake 编译失败:\n{stdout}\n{stderr}"

    # 安装
    install_cmd = ["cmake", "--install", ".", "--config", build_type]
    if install_dir != "/usr/local":
        install_cmd.append(f"--prefix={install_dir}")

    success, stdout, stderr = run_command(install_cmd, cwd=build_dir)
    if not success:
        return False, f"CMake 安装失败:\n{stdout}\n{stderr}"

    return True, ""


def build_makefile(source_dir: str, build_dir: str, install_dir: str,
                   toolchain_prefix: str, make_flags: str,
                   parallel: int) -> tuple:
    """使用 Makefile 构建"""
    if build_dir != source_dir:
        # 尝试创建输出目录
        os.makedirs(build_dir, exist_ok=True)

        # 检测是否是带 configure 的 Makefile
        if os.path.exists(os.path.join(source_dir, "configure")):
            # 运行 configure
            configure_cmd = ["./configure", f"--prefix={install_dir}"]
            success, stdout, stderr = run_command(configure_cmd, cwd=source_dir)
            if not success:
                return False, f"configure 失败:\n{stdout}\n{stderr}"

    # 设置环境变量
    env = os.environ.copy()
    env["CROSS_COMPILE"] = toolchain_prefix
    env["CC"] = f"{toolchain_prefix}gcc"
    env["CXX"] = f"{toolchain_prefix}g++"
    env["AR"] = f"{toolchain_prefix}ar"
    env["RANLIB"] = f"{toolchain_prefix}ranlib"

    # 编译
    make_cmd = ["make"]
    if parallel > 0:
        make_cmd.extend([f"-j{parallel}"])
    if make_flags:
        make_cmd.extend(make_flags.split())

    # 确定工作目录
    work_dir = source_dir if os.path.exists(os.path.join(source_dir, "Makefile")) else build_dir

    success, stdout, stderr = run_command(make_cmd, cwd=work_dir, env=env)
    if not success:
        return False, f"Make 编译失败:\n{stdout}\n{stderr}"

    # 安装
    install_cmd = ["make", "install"]
    if make_flags:
        install_cmd.extend(make_flags.split())

    env["DESTDIR"] = install_dir if install_dir else ""

    success, stdout, stderr = run_command(install_cmd, cwd=work_dir, env=env)
    if not success:
        return False, f"Make 安装失败:\n{stdout}\n{stderr}"

    return True, ""


def build_autotools(source_dir: str, build_dir: str, install_dir: str,
                    toolchain_prefix: str, make_flags: str,
                    parallel: int) -> tuple:
    """使用 Autotools 构建"""
    if not os.path.exists(os.path.join(source_dir, "configure")):
        # 生成 configure
        success, _, stderr = run_command(["./autogen.sh"], cwd=source_dir)
        if not success:
            # 尝试使用 autoreconf
            success, _, stderr = run_command(["autoreconf", "-i"], cwd=source_dir)
            if not success:
                return False, f"生成 configure 失败:\n{stderr}"

    # 配置
    configure_cmd = [
        "./configure",
        f"--prefix={install_dir}",
        f"--host={toolchain_prefix.rstrip('-')}"
    ]

    success, stdout, stderr = run_command(configure_cmd, cwd=source_dir)
    if not success:
        return False, f"configure 失败:\n{stdout}\n{stderr}"

    # 编译
    make_cmd = ["make"]
    if parallel > 0:
        make_cmd.extend([f"-j{parallel}"])
    if make_flags:
        make_cmd.extend(make_flags.split())

    success, stdout, stderr = run_command(make_cmd, cwd=source_dir)
    if not success:
        return False, f"Make 编译失败:\n{stdout}\n{stderr}"

    # 安装
    env = os.environ.copy()
    env["DESTDIR"] = install_dir if install_dir else ""

    success, stdout, stderr = run_command(["make", "install"], cwd=source_dir, env=env)
    if not success:
        return False, f"Make 安装失败:\n{stdout}\n{stderr}"

    return True, ""


def build_cargo(source_dir: str, build_dir: str, install_dir: str,
                toolchain_prefix: str, target: str,
                release: bool) -> tuple:
    """使用 Cargo 构建"""
    env = os.environ.copy()
    env["TARGET_CC"] = f"{toolchain_prefix}gcc"
    env["TARGET_CXX"] = f"{toolchain_prefix}g++"
    env["TARGET_AR"] = f"{toolchain_prefix}ar"
    env["TARGET_LINKER"] = f"{toolchain_prefix}gcc"

    # 获取目标 triple
    target_map = {
        "arm-linux-gnueabihf-": "thumbv7em-none-eabihf",
        "arm-linux-gnueabi-": "thumbv7em-none-eabi",
        "aarch64-linux-gnu-": "aarch64-unknown-linux-gnu",
        "riscv64-unknown-elf-": "riscv64gc-unknown-none-elf",
    }
    cargo_target = target_map.get(toolchain_prefix, target)

    build_cmd = ["cargo", "build"]
    if release:
        build_cmd.append("--release")
    if cargo_target:
        build_cmd.extend(["--target", cargo_target])

    success, stdout, stderr = run_command(build_cmd, cwd=source_dir, env=env)
    if not success:
        return False, f"Cargo 构建失败:\n{stdout}\n{stderr}"

    # 安装
    env["PREFIX"] = install_dir
    success, stdout, stderr = run_command(["cargo", "install", "--force"], cwd=source_dir, env=env)
    if not success:
        # 尝试复制二进制文件
        profile = "release" if release else "debug"
        src_bin = os.path.join(source_dir, "target", cargo_target, profile)
        if os.path.exists(src_bin):
            os.makedirs(os.path.join(install_dir, "bin"), exist_ok=True)
            for f in os.listdir(src_bin):
                if os.path.isfile(os.path.join(src_bin, f)):
                    shutil.copy(os.path.join(src_bin, f), os.path.join(install_dir, "bin", f))

    return True, ""


def get_parallel_jobs(requested: int) -> int:
    """获取并行编译核数"""
    if requested > 0:
        return requested

    # 自动检测 CPU 核数
    try:
        import multiprocessing
        return multiprocessing.cpu_count()
    except:
        return 1


def collect_artifacts(directory: str, extensions: list = None) -> list:
    """收集构建产物"""
    artifacts = []
    if extensions is None:
        extensions = [".so", ".a", ".o", ".elf", ".bin", ".hex"]

    for root, dirs, files in os.walk(directory):
        for f in files:
            if any(f.endswith(ext) or ext in f for ext in extensions):
                artifacts.append(os.path.join(root, f))

    return artifacts


def validate_install_path(path: str, blocked_paths: list) -> tuple:
    """验证安装路径"""
    abs_path = os.path.abspath(path)

    for blocked in blocked_paths:
        if abs_path.startswith(os.path.abspath(blocked)):
            return False, f"禁止安装到系统目录: {blocked}"

    return True, ""


def main():
    parser = argparse.ArgumentParser(
        description="交叉编译构建工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s -s source.tar.gz -o build -i /opt/install -t arm-linux-gnueabihf-
  %(prog)s -s ./mylib -o build -i /opt/install -tp armv7
  %(prog)s -s project -o build -i /opt/install --detect-only
        """
    )

    parser.add_argument("-s", "--source", required=True, help="源码包路径或目录")
    parser.add_argument("-o", "--output", required=True, help="编译输出目录")
    parser.add_argument("-i", "--install", required=True, help="安装目标目录")
    parser.add_argument("-t", "--toolchain", help="交叉编译工具链前缀（如 arm-linux-gnueabihf-）")
    parser.add_argument("-tp", "--toolchain-path", help="工具链根目录")
    parser.add_argument("-tf", "--toolchain-file", help="CMake 工具链文件路径")
    parser.add_argument("-bt", "--build-type", default="Release", choices=["Debug", "Release", "RelWithDebInfo", "MinSizeRel"], help="构建类型")
    parser.add_argument("-j", "--parallel", type=int, default=0, help="并行编译核数（0=自动）")
    parser.add_argument("-ec", "--extra-cmake", default="", help="额外的 CMake 参数")
    parser.add_argument("-em", "--extra-make", default="", help="额外的 Make 参数")
    parser.add_argument("-d", "--detect-only", action="store_true", help="仅检测构建系统，不执行编译")
    parser.add_argument("-n", "--dry-run", action="store_true", help="模拟执行")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("-c", "--cwd", default=os.getcwd(), help="工作目录")
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--toolchain-preset", help="使用预定义工具链（armv7/armv8/riscv32/riscv64）")

    args = parser.parse_args()

    # 加载配置
    config = load_config(args.config)

    # 处理工具链预设
    if args.toolchain_preset:
        if args.toolchain_preset in config.toolchain_presets:
            preset = config.toolchain_presets[args.toolchain_preset]
            if not args.toolchain:
                args.toolchain = preset.get("prefix", config.toolchain_prefix)
            if not args.toolchain_path:
                toolchain_path = preset.get("cmake_flags", "")
                if "SYSROOT" in toolchain_path:
                    # 从 cmake_flags 中提取路径
                    for part in toolchain_path.split():
                        if part.startswith("-DCMAKE_SYSROOT="):
                            args.toolchain_path = part.split("=")[1]
                            break
        else:
            print(f"错误：未知的工具链预设: {args.toolchain_preset}")
            print(f"可用预设: {', '.join(config.toolchain_presets.keys())}")
            sys.exit(1)

    # 使用配置或命令行参数
    toolchain_prefix = args.toolchain or config.toolchain_prefix
    toolchain_path = args.toolchain_path or config.toolchain_path
    parallel = args.parallel if args.parallel > 0 else get_parallel_jobs(config.parallel_jobs)
    install_dir = args.install or config.default_install_prefix

    # 安全检查
    if config.security_enabled:
        valid, msg = validate_install_path(install_dir, config.blocked_paths)
        if not valid:
            if args.json:
                print(json.dumps({
                    "status": "failure",
                    "summary": "安装路径验证失败",
                    "failure_category": "security_error",
                    "error_message": msg
                }))
            else:
                print(f"错误：{msg}")
            sys.exit(1)

    start_time = datetime.now()

    if args.json:
        print(json.dumps({
            "status": "info",
            "summary": "开始交叉编译",
            "source": args.source,
            "toolchain": toolchain_prefix
        }))

    # 解压源码
    source_path = Path(args.source)
    if source_path.is_file():
        if args.json:
            print(json.dumps({"status": "info", "step": "extract", "message": f"解压: {source_path}"}))
        temp_dir = tempfile.mkdtemp()
        try:
            actual_source = extract_archive(str(source_path), temp_dir)
        except Exception as e:
            result = BuildResult(
                status="failure",
                summary="解压源码失败",
                failure_category="extract_error",
                error_code="CCB_102",
                error_message=str(e),
                suggestions=["检查压缩包格式是否支持", "支持的格式: .tar.gz, .tar.bz2, .tar.xz, .zip"]
            )
            print(json.dumps(result.__dict__) if args.json else print(result.summary))
            sys.exit(1)
    else:
        actual_source = str(source_path)

    # 检测构建系统
    if args.json:
        print(json.dumps({"status": "info", "step": "detect", "message": "检测构建系统..."}))

    build_system = detect_build_system(actual_source)

    if args.json:
        print(json.dumps({"status": "info", "step": "detect", "result": build_system.value}))

    if build_system == BuildSystem.UNKNOWN:
        result = BuildResult(
            status="failure",
            summary="未检测到支持的构建系统",
            source_path=actual_source,
            failure_category="build_system_not_detected",
            error_code="CCB_103",
            suggestions=["确保源码包含 CMakeLists.txt 或 Makefile", "检查源码目录是否正确"]
        )
        print(json.dumps(result.__dict__) if args.json else result.summary)
        sys.exit(1)

    if args.detect_only:
        result = {
            "status": "success",
            "summary": "构建系统检测完成",
            "source_path": actual_source,
            "build_system": build_system.value,
            "message": f"检测到构建系统: {build_system.value}"
        }
        print(json.dumps(result) if args.json else result["message"])
        sys.exit(0)

    # 检查工具链
    if args.json:
        print(json.dumps({"status": "info", "step": "check_toolchain", "message": f"检查工具链: {toolchain_prefix}"}))

    valid, msg = check_toolchain(toolchain_prefix, toolchain_path)
    if not valid:
        result = BuildResult(
            status="failure",
            summary="工具链检查失败",
            toolchain=toolchain_prefix,
            failure_category="toolchain_missing",
            error_code="CCB_104",
            error_message=msg,
            suggestions=[
                "确认交叉编译工具链已安装",
                f"安装命令: sudo apt install gcc-arm-linux-gnueabihf",
                f"或指定工具链路径: --toolchain-path /opt/toolchains"
            ]
        )
        print(json.dumps(result.__dict__) if args.json else result.summary)
        sys.exit(1)

    # 创建构建目录
    os.makedirs(args.output, exist_ok=True)

    # 执行构建
    if args.dry_run:
        result = {
            "status": "success",
            "summary": "模拟执行完成",
            "source_path": actual_source,
            "build_system": build_system.value,
            "toolchain": toolchain_prefix,
            "output_dir": args.output,
            "install_dir": install_dir,
            "message": "这是模拟执行，未实际进行编译"
        }
        print(json.dumps(result) if args.json else result["message"])
        sys.exit(0)

    if args.json:
        print(json.dumps({"status": "info", "step": "build", "message": f"开始构建: {build_system.value}"}))

    success = False
    error_msg = ""

    cmake_flags = config.default_cmake_flags
    if args.extra_cmake:
        cmake_flags += " " + args.extra_cmake

    make_flags = config.default_make_flags
    if args.extra_make:
        make_flags += " " + args.extra_make

    if build_system == BuildSystem.CMAKE:
        success, error_msg = build_cmake(
            actual_source, args.output, install_dir,
            toolchain_prefix, toolchain_path,
            cmake_flags, make_flags, parallel, args.build_type
        )
    elif build_system == BuildSystem.MAKEFILE:
        success, error_msg = build_makefile(
            actual_source, args.output, install_dir,
            toolchain_prefix, make_flags, parallel
        )
    elif build_system == BuildSystem.AUTOTOOLS:
        success, error_msg = build_autotools(
            actual_source, args.output, install_dir,
            toolchain_prefix, make_flags, parallel
        )
    elif build_system == BuildSystem.CARGO:
        success, error_msg = build_cargo(
            actual_source, args.output, install_dir,
            toolchain_prefix, "", args.build_type == "Release"
        )

    end_time = datetime.now()
    build_time = str(end_time - start_time)

    # 收集产物
    artifacts = collect_artifacts(args.output)
    install_paths = []
    if os.path.exists(install_dir):
        install_paths = collect_artifacts(install_dir)

    if success:
        result = BuildResult(
            status="success",
            summary="交叉编译完成",
            source_path=actual_source,
            build_system=build_system.value,
            output_dir=args.output,
            install_dir=install_dir,
            toolchain=toolchain_prefix,
            build_time=build_time,
            artifacts=artifacts,
            install_paths=install_paths
        )
    else:
        result = BuildResult(
            status="failure",
            summary="交叉编译失败",
            source_path=actual_source,
            build_system=build_system.value,
            output_dir=args.output,
            install_dir=install_dir,
            toolchain=toolchain_prefix,
            build_time=build_time,
            failure_category="build_error",
            error_code="CCB_201",
            error_message=error_msg,
            suggestions=[
                "检查源码是否有语法错误",
                "确认所有依赖库已安装",
                "查看上方错误信息"
            ]
        )

    if args.json:
        print(json.dumps(result.__dict__, indent=2))
    else:
        print(result.summary)
        if success:
            print(f"构建系统: {result.build_system}")
            print(f"工具链: {result.toolchain}")
            print(f"构建时间: {result.build_time}")
            if artifacts:
                print(f"构建产物: {len(artifacts)} 个文件")
            if install_paths:
                print(f"安装文件: {len(install_paths)} 个文件")
        else:
            print(f"错误: {result.error_message}")
            for suggestion in result.suggestions:
                print(f"建议: {suggestion}")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
