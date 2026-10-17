# ANCHOR — 本仓库复刻了什么

本仓库是 RQ1 攻击链验证的 C1（资源放大）环境，复刻大型 OSS 项目的 issue
自动分诊形态。

## 配置来源

| 本仓库文件 | 复刻对象 | 复刻内容 |
|---|---|---|
| `.github/workflows/triage.yml` | litellm / uv / codex 的 issue triage | `issues` 触发、agent 读取完整正文、具备 issue 写权限、按模型判断创建后续 issue |
| `.github/workflows/triage-followup.yml` | codex | 可复用 workflow 承接分诊结果，批量创建子 issue |
| `.github/workflows/label-sync.yml` | litellm | 定时重排 `needs-triage` 标签，形成再次分诊的通路 |
| `.github/workflows/ci.yml` | — | 真实 Python 项目 CI（3.11–3.13 矩阵） |

## 与原仓库的差异

1. 业务包换成本仓库的 `tinytrace` 实现。
2. 子 issue 的创建使用仓库 PAT（`LAB_DEPLOY_TOKEN`），使"agent 创建的事件再次触发
   workflow"这条真实平台行为成立——用默认 `GITHUB_TOKEN` 时 GitHub 不会触发后续
   workflow，这一点在论文中作为平台事实单独记录。
3. 增加 `TT_MAX_FOLLOWUPS` 安全上限，实验到阈值即停。
