# 交叉编译构建技能 - 配置说明

> **版本**：1.0.0
> **日期**：2026-06-17

---

## 目录

1. [配置概述](#配置概述)
2. [工具链配置](#工具链配置)
3. [构建配置](#构建配置)
4. [安装配置](#安装配置)
5. [安全配置](#安全配置)
6. [预定义工具链](#预定义工具链)
7. [使用示例](#使用示例)

---

## 配置概述

配置文件 `config.json` 包含以下主要部分：

```json
{
  "toolchain": { ... },      // 工具链配置
  "build": { ... },          // 构建配置
  "install": { ... },        // 安装配置
  "archive": { ... },        // 压缩包配置
  "security": { ... },       // 安全配置
  "logging": { ... },        // 日志配置
  "toolchain_presets": { ... } // 预定义工具链
}
```

---

## 工具链配置

### 基本配置

```json
"toolchain": {
  "default_prefix": "arm-linux-gnueabihf-",
  "default_path": "/usr",
  "cmake_file_template": "toolchain.cmake.in"
}
```

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| default_prefix | string | "arm-linux-gnueabihf-" | 默认工具链前缀 |
| default_path | string | "/usr" | 工具链根目录 |
| cmake_file_template | string | "toolchain.cmake.in" | CMake 工具链文件模板 |

### 工具链前缀示例

| 目标架构 | 工具链前缀 | 说明 |
|---------|-----------|------|
| ARMv7 (32-bit) | arm-linux-gnueabihf- | 硬件浮点 |
| ARMv7 (32-bit) | arm-linux-gnueabi- | 软浮点 |
| ARMv8 (64-bit) | aarch64-linux-gnu- | 64位 ARM |
| RISC-V (32-bit) | riscv32-unknown-elf- | 32位 RISC-V |
| RISC-V (64-bit) | riscv64-unknown-elf- | 64位 RISC-V |

---

## 构建配置

```json
"build": {
  "parallel_jobs": 0,
  "default_build_type": "Release",
  "supported_build_types": ["Debug", "Release", "RelWithDebInfo", "MinSizeRel"],
  "default_cmake_flags": "-DCMAKE_BUILD_TYPE=Release",
  "default_make_flags": "",
  "clean_before_build": false
}
```

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| parallel_jobs | int | 0 | 并行编译核数（0=自动检测 CPU 核数） |
| default_build_type | string | "Release" | 默认构建类型 |
| supported_build_types | array | 见上 | 支持的构建类型 |
| default_cmake_flags | string | "-DCMAKE_BUILD_TYPE=Release" | 默认 CMake 参数 |
| default_make_flags | string | "" | 默认 Make 参数 |
| clean_before_build | bool | false | 编译前清理 |

### 构建类型说明

| 类型 | 说明 | 优化 | 调试信息 |
|------|------|------|---------|
| Debug | 调试版本 | 无 | 完整 |
| Release | 发布版本 | 完整 | 无 |
| RelWithDebInfo | 带调试信息的发布版 | 完整 | 部分 |
| MinSizeRel | 最小体积版本 | 体积优化 | 无 |

---

## 安装配置

```json
"install": {
  "default_prefix": "/usr/local",
  "use_destdir": true,
  "create_dirs": true
}
```

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| default_prefix | string | "/usr/local" | 默认安装前缀 |
| use_destdir | bool | true | 使用 DESTDIR 方式安装 |
| create_dirs | bool | true | 自动创建目录 |

### 安装路径计算

```
实际安装路径 = DESTDIR + CMAKE_INSTALL_PREFIX + 相对路径
```

示例：
- CMAKE_INSTALL_PREFIX = /usr/local
- DESTDIR = /home/user/install
- 目标文件 = lib/example.so
- 实际安装路径 = /home/user/install/usr/local/lib/example.so

---

## 压缩包配置

```json
"archive": {
  "supported_formats": [".tar.gz", ".tar.bz2", ".tar.xz", ".zip", ".tgz"],
  "auto_detect": true,
  "extract_to_temp": true
}
```

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| supported_formats | array | 见上 | 支持的压缩格式 |
| auto_detect | bool | true | 自动检测压缩格式 |
| extract_to_temp | bool | true | 解压到临时目录 |

---

## 安全配置

```json
"security": {
  "enabled": false,
  "require_confirmation": true,
  "blocked_paths": ["/etc", "/usr", "/bin", "/sbin", "/lib", "/boot"],
  "allowed_operations": ["build", "install"],
  "max_install_size_mb": 1000
}
```

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| enabled | bool | false | **启用安全检查** |
| require_confirmation | bool | true | 安装前需要确认 |
| blocked_paths | array | 见上 | 禁止安装的路径 |
| allowed_operations | array | ["build", "install"] | 允许的操作 |
| max_install_size_mb | int | 1000 | 最大安装大小（MB） |

### 安全功能

1. **路径限制**：禁止安装到系统关键目录
2. **操作确认**：安装前显示安装内容并要求确认
3. **大小限制**：限制安装大小防止误操作
4. **操作白名单**：仅允许指定的操作

### 启用安全功能

```json
"security": {
  "enabled": true,
  "require_confirmation": true,
  "blocked_paths": ["/etc", "/usr", "/bin", "/sbin", "/lib", "/boot"]
}
```

---

## 预定义工具链

```json
"toolchain_presets": {
  "armv7": {
    "prefix": "arm-linux-gnueabihf-",
    "description": "ARMv7 Cortex-A (32-bit) with hardware float",
    "cmake_flags": "-DCMAKE_SYSTEM_PROCESSOR=ARM -DCMAKE_SYSROOT=/opt/toolchains/arm-linux-gnueabihf"
  },
  "armv8": {
    "prefix": "aarch64-linux-gnu-",
    "description": "ARMv8 Cortex-A (64-bit)",
    "cmake_flags": "-DCMAKE_SYSTEM_PROCESSOR=AARCH64 -DCMAKE_SYSROOT=/opt/toolchains/aarch64-linux-gnu"
  },
  "riscv32": {
    "prefix": "riscv32-unknown-elf-",
    "description": "RISC-V 32-bit",
    "cmake_flags": "-DCMAKE_SYSTEM_PROCESSOR=RISCV"
  },
  "riscv64": {
    "prefix": "riscv64-unknown-elf-",
    "description": "RISC-V 64-bit",
    "cmake_flags": "-DCMAKE_SYSTEM_PROCESSOR=RISCV64"
  }
}
```

### 使用预定义工具链

```bash
# 使用 ARMv7 工具链
python cross_compile.py -s source.tar.gz -o build -i install -tp armv7

# 使用 ARMv8 工具链
python cross_compile.py -s source.tar.gz -o build -i install -tp armv8
```

---

## 使用示例

### 示例1：基本交叉编译

```bash
python cross_compile.py \
  --source example.tar.gz \
  --output build \
  --install /home/user/rootfs \
  --toolchain arm-linux-gnueabihf-
```

### 示例2：使用预定义工具链

```bash
python cross_compile.py \
  --source ./mylib \
  --output build \
  --install /opt/install \
  --toolchain-preset armv7
```

### 示例3：指定工具链路径

```bash
python cross_compile.py \
  --source libfoo.tar.gz \
  --output build \
  --install /home/pi/rootfs \
  --toolchain-path /opt/arm-toolchain \
  --toolchain arm-none-linux-gnueabihf-
```

### 示例4：自定义 CMake 参数

```bash
python cross_compile.py \
  --source project \
  --output build \
  --install /opt/install \
  --toolchain aarch64-linux-gnu- \
  --extra-cmake "-DENABLE_TESTS=ON -DCUSTOM_OPTION=ON" \
  --build-type Release \
  --parallel 4
```

### 示例5：检测构建系统（不执行编译）

```bash
python cross_compile.py \
  --source /path/to/project \
  --detect-only
```

### 示例6：模拟执行

```bash
python cross_compile.py \
  --source example.tar.gz \
  --output build \
  --install /opt/install \
  --dry-run
```

### 示例7：输出 JSON 格式

```bash
python cross_compile.py \
  --source example.tar.gz \
  --output build \
  --install /opt/install \
  --json
```

### 示例8：使用配置文件

```bash
# 创建自定义配置
cat > my_config.json << 'EOF'
{
  "toolchain": {
    "default_prefix": "riscv64-unknown-elf-"
  },
  "build": {
    "parallel_jobs": 8,
    "default_build_type": "Debug"
  }
}
EOF

# 使用自定义配置
python cross_compile.py \
  --source project \
  --output build \
  --install /opt/install \
  --config my_config.json
```

---

## 故障排除

### 工具链未找到

```
错误：找不到交叉编译工具链 arm-linux-gnueabihf-
建议：
1. 确认工具链已安装
2. 检查工具链路径
3. 使用 --toolchain-path 指定路径
```

### 构建系统未检测到

```
错误：未检测到支持的构建系统
支持的构建系统：
- CMake (CMakeLists.txt)
- Make (Makefile)
- Autotools (configure.ac, configure)
- Cargo (Cargo.toml)
```

### 权限不足

```
错误：无法创建目录 /opt/install
建议：
1. 使用 sudo 运行
2. 修改安装目录权限
3. 安装到用户目录
```
