# 交叉编译构建技能

> **版本**：1.0.0
> **日期**：2026-06-17
> **类型**：平台技能
> **功能**：解压源码包、自动检测构建系统、执行交叉编译、安装到指定位置

---

## 元数据

| 字段 | 值 |
|------|-----|
| name | cross-compile-build |
| version | 1.0.0 |
| description | 交叉编译构建技能，支持解压、自动检测构建系统、交叉编译和安装 |
| keywords | ["交叉编译", "cross-compile", "arm", "cmake", "makefile", "嵌入式", "安装"] |
| platforms | ["linux", "windows"] |
| required_tools | ["git", "cmake", "make", "tar", "unzip"] |
| output_format | structured |
| author | "Plumb-Link Team" |
| license | "MIT" |

---

## 触发条件

### 触发关键词

- "交叉编译"
- "cross-compile"
- "arm编译"
- "嵌入式编译"
- "交叉编译构建"
- "编译到目标板"

### 触发场景

1. 用户需要编译嵌入式项目到 ARM/ARM64 目标板
2. 用户需要解压源码包并进行交叉编译
3. 用户需要配置不同的交叉编译工具链

---

## 执行步骤

### 步骤1：解压源码包

```bash
# 支持 .tar.gz, .tar.bz2, .tar.xz, .zip 等格式
tar -xzf source.tar.gz -C <解压目录>
# 或
unzip source.zip -d <解压目录>
```

### 步骤2：自动检测构建系统

```bash
# 检测 CMakeLists.txt → 使用 cmake 构建
# 检测 Makefile → 使用 make 构建
# 检测 configure.ac/configure → 使用 autotools 构建
# 检测 Cargo.toml → 使用 cargo 构建
# 检测 CMakeLists.txt + Makefile → 优先 cmake
```

### 步骤3：配置交叉编译工具链

```bash
# 用户指定工具链路径和前缀
export CC=<toolchain>-gcc
export CXX=<toolchain>-g++
export AR=<toolchain>-ar
export RANLIB=<toolchain>-ranlib
export CROSS_COMPILE=<toolchain>-
```

### 步骤4：执行交叉编译

```bash
# CMake 构建方式
mkdir build && cd build
cmake -DCMAKE_TOOLCHAIN_FILE=<toolchain-file> <source_dir>
make -j$(nproc)

# Makefile 构建方式
make CROSS_COMPILE=<toolchain>-
```

### 步骤5：安装到指定位置

```bash
# 安装到用户指定目录
make DESTDIR=<install_dir> install
# 或
cmake -DCMAKE_INSTALL_PREFIX=<install_dir> ..
make install
```

---

## 命令行参数

| 参数 | 缩写 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| --source | -s | string | 是 | 源码包路径或目录 |
| --output | -o | string | 是 | 编译输出目录 |
| --install | -i | string | 是 | 安装目标目录 |
| --toolchain | -t | string | 否 | 交叉编译工具链前缀（如 arm-linux-gnueabihf-） |
| --toolchain-path | -tp | string | 否 | 工具链根目录 |
| --toolchain-file | -tf | string | 否 | CMake 工具链文件 |
| --build-type | -bt | string | 否 | 构建类型：Debug/Release |
| --parallel | -j | int | 否 | 并行编译核数 |
| --extra-cmake | -ec | string | 否 | 额外的 CMake 参数 |
| --extra-make | -em | string | 否 | 额外的 Make 参数 |
| --detect-only | -d | flag | 否 | 仅检测构建系统，不执行编译 |
| --dry-run | -n | flag | 否 | 模拟执行 |
| --json | -j | flag | 否 | 输出 JSON 格式结果 |
| --cwd | -c | string | 否 | 工作目录 |
| --config | -cf | string | 否 | 配置文件路径 |

---

## 输出格式

### 成功输出

```json
{
  "status": "success",
  "summary": "交叉编译完成",
  "evidence": {
    "source_path": "/path/to/source",
    "build_system": "cmake",
    "output_dir": "/path/to/build",
    "install_dir": "/path/to/install",
    "toolchain": "arm-linux-gnueabihf-",
    "build_time": "120s",
    "artifacts": [
      "/path/to/build/libexample.so",
      "/path/to/build/example"
    ],
    "install_paths": [
      "/path/to/install/lib/libexample.so",
      "/path/to/install/bin/example"
    ]
  }
}
```

### 失败输出

```json
{
  "status": "failure",
  "summary": "交叉编译失败",
  "failure_category": "build_error",
  "error_code": "CCB_001",
  "evidence": {
    "error_message": "cmake 配置失败：找不到交叉编译工具链",
    "last_command": "cmake -DCMAKE_TOOLCHAIN_FILE=... ..",
    "output_log": "..."
  },
  "suggestions": [
    "检查工具链路径是否正确",
    "确认工具链已安装"
  ]
}
```

---

## 失败分类

| 分类 | 代码 | 说明 | 建议 |
|------|------|------|------|
| source_not_found | CCB_101 | 源码包不存在 | 检查源码路径 |
| unsupported_archive | CCB_102 | 不支持的压缩格式 | 使用支持的格式 |
| build_system_not_detected | CCB_103 | 未检测到构建系统 | 确认源码包含构建文件 |
| toolchain_missing | CCB_104 | 工具链不存在 | 安装交叉编译工具链 |
| configure_failed | CCB_201 | 配置失败 | 检查 CMakeLists.txt 或 Makefile |
| build_failed | CCB_202 | 编译失败 | 查看编译错误日志 |
| install_failed | CCB_203 | 安装失败 | 检查安装目录权限 |
| permission_denied | CCB_301 | 权限不足 | 使用 sudo 或修改目录权限 |

---

## 配置项（config.json）

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| default_toolchain | string | "arm-linux-gnueabihf-" | 默认工具链前缀 |
| default_toolchain_path | string | "/usr" | 默认工具链路径 |
| default_install_prefix | string | "/usr/local" | 默认安装前缀 |
| parallel_jobs | int | 0 | 并行编译核数（0=自动检测） |
| build_types | array | ["Debug", "Release"] | 支持的构建类型 |
| supported_archives | array | [".tar.gz", ".tar.bz2", ".tar.xz", ".zip"] | 支持的压缩格式 |
| default_cmake_flags | string | "-DCMAKE_BUILD_TYPE=Release" | 默认 CMake 参数 |
| default_make_flags | string | "" | 默认 Make 参数 |
| security.enabled | bool | false | 安全开关 |
| security.allowed_operations | array | [] | 允许的操作 |
| security.blocked_paths | array | ["/etc", "/usr", "/bin"] | 禁止的路径 |

---

## 依赖工具

| 工具名称 | 用途 | 检测方法 |
|---------|------|---------|
| tar | 解压 tar 压缩包 | `tar --version` |
| unzip | 解压 zip 压缩包 | `unzip -v` |
| cmake | CMake 构建 | `cmake --version` |
| make | Make 构建 | `make --version` |
| gcc/g++ | C/C++ 编译器 | `gcc --version` |
| 交叉编译工具链 | 目标板编译 | `arm-linux-gnueabihf-gcc --version` |

---

## 安全注意事项

1. **工具链验证**：使用前验证交叉编译工具链存在
2. **路径限制**：禁止交叉编译到系统关键目录（/etc, /usr 等）
3. **权限控制**：安装到系统目录需要 sudo 权限
4. **输出校验**：验证编译输出文件的有效性
5. **日志记录**：记录完整的编译过程便于调试

---

## 参考资料

- [CMake 交叉编译指南](https://cmake.org/cmake/help/latest/manual/cmake-toolchains.7.html)
- [GNU ARM 交叉编译工具链](https://developer.arm.com/tools-and-software/open-source-software/developer-tools/gnu-toolchain/gnu-rm)
- [Yocto Project 交叉编译](https://www.yoctoproject.org/)
