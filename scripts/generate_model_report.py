"""
Turn `scripts/probe_report.json` into a human-readable markdown report at
`docs/MODEL_AVAILABILITY.md`.

This is a pure local transform. No network.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "scripts" / "probe_report.json"
OUT = ROOT / "docs" / "MODEL_AVAILABILITY.md"

REASON_ZH = {
    "ok": "可用",
    "http_429": "上游限流 / 额度不足 / 负载饱和",
    "model_not_found": "上游渠道不存在或已下线",
    "service_unavailable": "上游临时不可用（503）",
    "server_error": "上游服务器内部错误（500）",
    "bad_request": "请求参数被拒绝（该模型可能需要非 chat 协议，如图像/视频生成）",
    "no_permission": "API Key 无该模型权限",
    "timeout": "超时无响应",
    "network_error": "网络错误",
}


def main() -> int:
    if not REPORT.is_file():
        print(f"ERROR: {REPORT} not found. Run probe_all.py first.")
        return 1

    data = json.loads(REPORT.read_text(encoding="utf-8"))
    ok = [r for r in data if r.get("ok")]
    fail = [r for r in data if not r.get("ok")]

    reason_counts = Counter(r.get("reason", "unknown") for r in fail)

    lines: list[str] = []
    lines.append("# 魔芋AI 模型可用性报告")
    lines.append("")
    lines.append(f"> 生成时间：{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  ")
    lines.append("> 探活端点：`POST https://www.moyu.info/v1/chat/completions`  ")
    lines.append("> 探活请求：`{\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}], \"max_tokens\":1, \"stream\":false}`  ")
    lines.append("> 超时：30s × 最多 4 次重试")
    lines.append("")
    lines.append(f"## 汇总")
    lines.append("")
    lines.append(f"- 模型总数：**{len(data)}**")
    lines.append(f"- 可用（OK）：**{len(ok)}**")
    lines.append(f"- 不可用（FAIL）：**{len(fail)}**")
    lines.append("")
    lines.append("### 不可用原因分布")
    lines.append("")
    lines.append("| 原因码 | 含义 | 数量 |")
    lines.append("|--------|------|------|")
    for reason, count in reason_counts.most_common():
        meaning = REASON_ZH.get(reason, "—")
        lines.append(f"| `{reason}` | {meaning} | {count} |")
    lines.append("")

    lines.append("## 可直接调用的模型（OK）")
    lines.append("")
    lines.append("| # | 模型 ID | 平均耗时 |")
    lines.append("|---|---------|----------|")
    for i, r in enumerate(sorted(ok, key=lambda x: x["model"]), 1):
        lines.append(f"| {i} | `{r['model']}` | {r.get('elapsed', 0):.1f}s |")
    lines.append("")

    lines.append("## 当前不可用的模型（FAIL）")
    lines.append("")
    lines.append("> 注意：这些模型也已写入插件。Dify 界面能看到并启用它们，")
    lines.append("> 但在上游恢复之前调用会报错。当魔芋AI 修复对应渠道后，")
    lines.append("> 无需重新打包插件即可恢复使用。")
    lines.append("")
    lines.append("| # | 模型 ID | 原因码 | 含义 | 详情节选 |")
    lines.append("|---|---------|--------|------|----------|")
    for i, r in enumerate(sorted(fail, key=lambda x: (x.get("reason", ""), x["model"])), 1):
        reason = r.get("reason", "")
        meaning = REASON_ZH.get(reason, "—")
        detail = (r.get("detail") or "").replace("|", "\\|").replace("\n", " ")
        if len(detail) > 110:
            detail = detail[:107] + "…"
        lines.append(f"| {i} | `{r['model']}` | `{reason}` | {meaning} | {detail or '—'} |")
    lines.append("")

    lines.append("## 给用户的使用建议")
    lines.append("")
    lines.append("1. 在 Dify 中配置魔芋AI API Key 后，先尝试上表「可直接调用」里的模型。")
    lines.append("2. 部分 `http_429` 模型是账户当前额度被打满，换一把额度充足的 Key 可能立即恢复。")
    lines.append("3. 大量 `bad_request` 的模型（`doubao-seedream-*`、`kling-*`、`sora-*`、`jimeng_*` 等）属于 **图像 / 视频生成类**，魔芋AI 的 `chat/completions` 接口不支持它们。插件保留其定义仅供 Dify 识别型号，若后续魔芋AI 推出对应的多模态接口，我们再在插件层适配。")
    lines.append("4. `model_not_found` / `service_unavailable` / `server_error` 多为上游短期问题，过一段时间再试。")
    lines.append("")
    lines.append("## 原始数据")
    lines.append("")
    lines.append("完整 JSON：`scripts/probe_report.json`。")
    lines.append("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
