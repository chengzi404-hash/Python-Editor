# Python Editor

[![Quality](https://github.com/chengzi404-hash/Python-Editor/actions/workflows/quality.yml/badge.svg)](https://github.com/chengzi404-hash/Python-Editor/actions/workflows/quality.yml)
[![Test](https://github.com/chengzi404-hash/Python-Editor/actions/workflows/pytest.yml/badge.svg)](https://github.com/chengzi404-hash/Python-Editor/actions/workflows/pytest.yml)
[![License](https://img.shields.io/github/license/chengzi404-hash/Python-Editor)](LICENSE)

<div align="center">
  一款简洁高效的 Python 代码编辑器，支持语法高亮、自动补全、代码检查与多语言执行。
</div>

## ✨ 核心亮点

- **开箱即用** — 无需复杂配置，直接运行 `python main.py` 即可启动
- **多语言支持** — 支持 Python、JSON、XML、YAML、C/C++、Log 等文件类型
- **智能补全** — Python、C/C++ 上下文感知代码建议
- **代码质量检查** — 集成 Flake8、Pyright、py_compile
- **一键运行** — 支持 venv、conda、系统 Python 环境选择
- **插件扩展** — 丰富的插件生态，轻松自定义功能
- **双语界面** — 中文 / English 界面实时切换

## 🚀 快速开始

```bash
python main.py
```

## 📋 主要功能

### 多文档编辑
Tab 栏支持多个文件同时打开与切换

### 语法高亮
为 Python、JSON、XML、YAML、C/C++、Log 等文件提供彩色语法显示

### 智能补全
基于代码上下文自动弹出补全建议

### 代码检查
集成 Flake8、Pyright、py_compile 进行静态分析

### 一键运行
支持 venv、conda 和系统 Python 环境快速切换执行

### 插件系统
提供钩子事件机制，可扩展编辑器的自定义功能

### 主题切换
支持 Dark、Light、Solarized Dark 三种主题外观

### 国际化
内置中文和英文两种语言，可实时切换界面显示

## ⚙️ 配置与数据

| 类型 | 路径 |
|------|------|
| 全局配置 | `~/.python-editor/settings.json` |
| 项目配置 | `<project>/.editorconfig` |
| 全局插件 | `~/.python-editor/plugins/` |
| 项目插件 | `<project>/plugins/` |

## ✅ 质量保障

- **测试覆盖** — 280+ 自动化测试用例
- **持续集成** — Python 3.10~3.12 多版本测试
- **代码规范** — Ruff + MyPy 严格检查

---

<div align="center">
  Made with ❤️ by <a href="https://github.com/chengzi404-hash">chengzi404-hash</a>
</div>
