# Codex Capability Hub

中文 | [English](README.md)

一个用于 **按需唤醒 Codex 能力** 的轻量级框架：支持 skills、MCP servers、plugins，以及多阶段 workflow。

## 为什么需要它

在 Windows 上，如果 Codex app 启动时同时加载大量 skills、MCP servers、plugins，启动和界面加载会变得非常慢。Capability Hub 的核心目标是把启动热路径压到最小：默认只保留一个很轻的路由层，真正需要某类能力时，再由 Codex 自动唤醒对应 skill/MCP/plugin/workflow。

这可以 **显著提升 Windows 系统中 Codex app 的启动速度和界面加载速度**，尤其适合安装了很多 skills、插件、MCP 的重度用户。在一个真实 Windows 配置中，经过按需唤醒与瘦身热路径优化后，`plugin/list` 从约 10–15 秒降到约 22 ms，`skills/list` 从约 10 秒降到约 109 ms。不同机器和配置结果会不同，但设计目标很明确：先保证启动快，再按需获得强能力。

## 核心思路

- 启动时只保留极小的路由层。
- 用 JSON registry 描述“能力”。
- `codex-auto-wake` 根据自然语言请求匹配 capability 或 workflow。
- `codex-wake` 负责实际唤醒 skill、启用 MCP、启用 plugin，或推进 workflow。
- 一次性重能力用完后可以 sleep，避免长期拖慢启动。

## 这个项目是什么

- 一个轻量的常驻路由器：`codex-auto-wake`。
- 一个可逆执行器：`codex-wake`。
- 一套用户可自定义的 JSON 能力配置格式。
- 面向 Windows Codex app 的 PowerShell wrapper 和安装脚本。
- 一个框架，而不是固定能力包：用户可以接入自己的 skills、MCP servers、plugins。

## 这个项目不是什么

这个仓库 **不是** 私有 `~/.codex` 的备份。不要提交或发布：

- API key、token、`~/.codex/config.toml`。
- 私有 skills。
- 专有 plugin cache。
- 浏览器 profile、cookies、登录态。
- 任何项目私有数据。

## 快速开始

```powershell
git clone https://github.com/<you>/codex-capability-hub.git
cd codex-capability-hub
powershell -ExecutionPolicy Bypass -File .\powershell\install.ps1
```

测试路由：

```powershell
$env:USERPROFILE\.codex\repair-tools\codex-auto-wake.ps1 -Text "help me debug this failing test" -DryRun
$env:USERPROFILE\.codex\repair-tools\codex-wake.ps1 list
```

把下面文件中的片段复制到你的项目级或全局 `AGENTS.md`，即可让 Codex 在需要时自动唤醒能力：

```text
examples/AGENTS.capability-hub.example.md
```

## 配置自己的能力

安装后，编辑：

```text
%USERPROFILE%\.codex\repair-tools\capabilities.json
%USERPROFILE%\.codex\repair-tools\capability_workflows.json
%USERPROFILE%\.codex\repair-tools\capability_links.json
%USERPROFILE%\.codex\repair-tools\capability_interfaces.json
```

也可以用环境变量指定其他配置文件：

- `CODEX_CAPABILITIES_JSON`
- `CODEX_CAPABILITY_WORKFLOWS_JSON`
- `CODEX_CAPABILITY_LINKS_JSON`
- `CODEX_CAPABILITY_INTERFACES_JSON`
- `CODEX_PLUGIN_ALIASES_JSON`
- `CODEX_HOME`
- `CODEX_COLD_ARCHIVE`

## 常用命令

```powershell
codex-wake.ps1 list
codex-wake.ps1 explain debug
codex-wake.ps1 dry-run office
codex-wake.ps1 wake debug
codex-wake.ps1 sleep debug
codex-auto-wake.ps1 -Text "make a PPT and export PDF" -Apply
codex-auto-wake.ps1 -Text "find papers then write a report" -Apply -PreferWorkflow
codex-plugin-toggle.ps1 --lean-startup
codex-lean-hotpath.ps1 apply
codex-capability-inventory.ps1 --json
```

## 典型场景

- Office/PPT/PDF 插件默认冷藏，只有文档任务出现时才启用。
- 浏览器测试或截图任务出现时，才启用 Playwright/browser MCP。
- 涉及 Chrome 登录态、cookies、广泛文件系统访问时，要求用户有明确意图。
- 用 progressive workflow 串联多个能力，例如：查文献 → 写报告 → 做幻灯片。

## 项目结构

```text
scripts/      Python 核心实现
powershell/   Windows wrapper、安装与卸载脚本
examples/     安全示例 registry 和 AGENTS 片段
schemas/      capability registry JSON schema
docs/         架构、workflow、Windows 性能、安全文档
tests/        路由与 registry 测试
```

## 开发

```powershell
python -m compileall scripts
python -m pytest -q
```

更多架构与配置格式见 `docs/`。
