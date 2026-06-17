# 新技能检查清单

## 基础要求

- [ ] 选择一个小写连字符风格的目录名（如 `build-linux-app`）
- [ ] 添加 frontmatter，并确保 `name` 与目录名一致
- [ ] `description` 能准确描述触发场景
- [ ] 使用技能模板中的全部必需章节

## 共享约定

- [ ] 复用共享模块，不要自行发明新的输出形状
- [ ] 使用 `shared/tool_config.py` 管理工具路径
- [ ] 使用 `shared/project_detect.py` 进行项目探测
- [ ] 使用 `shared/toolchain_env.py` 检测工具链环境

## 优先级规则

- [ ] 明确写出工具选择、配置选择和默认行为的优先级规则
- [ ] 遵循：CLI参数 → 配置文件 → 环境变量 → 硬编码路径 → PATH

## 失败处理

- [ ] 写清这个 skill 可能输出哪些失败分类
- [ ] 失败分类参考 `shared/failure-taxonomy.md`
- [ ] 明确哪些情况需要阻塞并询问用户

## 平台兼容

- [ ] 只有当平台差异会改变执行方式时，才写入平台相关说明
- [ ] 使用 `detect_os()` 进行跨平台判断
- [ ] 处理 Windows/Linux/macOS 的路径差异

## 交接关系

- [ ] 至少说明一个现有 skill 作为下游交接目标
- [ ] 提供清晰的推荐逻辑

## 测试验证

- [ ] 编写单元测试用例
- [ ] 覆盖正常路径和边界场景
- [ ] 执行 `python scripts/validate_repo.py`（如可用）

## 文档完善

- [ ] 补充示例交互
- [ ] 添加必要的注释
- [ ] 更新技能注册表

---

## 目录结构检查

```
skills/{{category}}/{{skill_name}}/
├── scripts/
│   └── src/
│       └── main.py          ✓ 主脚本入口
├── agents/                  ✓ AI 配置（如需要）
│   └── *.yaml
└── SKILL.md                 ✓ 技能定义文档
```

---

## 脚本规范检查

- [ ] 使用 `#!/usr/bin/env python3` shebang
- [ ] 包含类型注解
- [ ] 处理命令行参数
- [ ] 错误处理和异常捕获
- [ ] 使用日志记录
- [ ] 返回合适的退出码
