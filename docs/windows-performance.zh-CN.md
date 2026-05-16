# Windows 性能优化

中文 | [English](windows-performance.md)

Capability Hub 的一个核心目标，是通过缩小启动热路径，显著改善 Windows 上 Codex app 的启动速度和界面加载速度。

## 问题来源

在 Windows 上，如果大量可选能力一直处于 hot 状态，Codex 可能会明显变慢：

- 大量 skill 目录会增加文件扫描成本。
- 如果启用很多 plugin，或者 plugin cache 元数据不稳定，plugin discovery 可能成为界面加载瓶颈。
- MCP server 即使当前任务不需要，也可能在启用状态下带来启动负担。

## 优化策略

Windows 推荐默认状态：

- 大型 skill pack 默认冷藏。
- `[features].plugins = false`，直到任务确实需要插件能力。
- 热路径里只保留极小的系统 skill。
- MCP 尽量使用已安装的直接命令，减少 `npx`/`uvx` 之类 wrapper 的额外开销。
- 用户请求明确需要某能力时，再按需唤醒。
- 一次性重能力用完后 sleep，避免长期拖慢启动。

## 实测改善示例

在一个真实 Windows 配置中，把重 skills/plugins/MCP 改成按需唤醒后，与 Codex app 加载相关的操作有明显改善：

| 操作 | 优化前 | 优化后 |
| --- | ---: | ---: |
| `plugin/list` | 约 10–15 秒 | 约 22 ms |
| `skills/list` | 约 10 秒 | 约 109 ms |

实际结果会受硬件、已安装能力数量、plugin cache 状态、杀毒软件扫描、Codex 版本等影响。这个框架不承诺固定跑分，但它针对的是核心瓶颈：启动时加载了太多暂时用不到的东西。

## 恢复瘦身启动状态

```powershell
$env:USERPROFILE\.codex\repair-tools\codex-plugin-toggle.ps1 --lean-startup
$env:USERPROFILE\.codex\repair-tools\codex-lean-hotpath.ps1 apply
```

## 优化前后做度量

建议用诊断工具先定位是哪一层变热，而不是靠猜：

```powershell
$env:USERPROFILE\.codex\repair-tools\codex-capability-health.ps1
$env:USERPROFILE\.codex\repair-tools\codex-capability-benchmark.ps1
$env:USERPROFILE\.codex\repair-tools\codex-capability-doctor.ps1
```

推荐流程：

1. 先运行 `codex-capability-health.ps1`，看热路径风险。
2. 优化前后运行 `codex-capability-benchmark.ps1`，对比趋势。
3. 运行 `codex-capability-doctor.ps1`，获取安全的修复命令。
4. 如果改动了 skills、MCP 或 plugins，重启或 reload Codex 后再验证。

## 修复 bundled plugin cache

如果 OpenAI bundled plugin cache 被锁定或损坏，可以尝试：

```powershell
$env:USERPROFILE\.codex\repair-tools\codex-plugin-toggle.ps1 --repair-cache
```

## 不改变状态的路由验证

```powershell
$env:USERPROFILE\.codex\repair-tools\codex-auto-wake.ps1 -Text "make a PPT and export PDF" -DryRun
```
