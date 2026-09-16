# Alpha Lab OS：第一版设计

## 研究目标

把 Binance Web3 API 变成一个有时间一致性的研究数据源，先回答：

1. 市场状态、流量和流动性是否对未来收益有可测关系？
2. 钱包标签或交易流的成交后 markout 是否超出 momentum/liquidity 基线？
3. 不同交易规模下的报价曲线、路线分歧和冲击如何变化？
4. 代币生命周期与持仓结构变化是否形成可复现的事件信号？

## 数据层

```text
Binance Web3 API (read-only)
        |
        +-- Radar: price-info batch, hot-token universe
        +-- Research: candles, advanced-info, optional dev/holder state
        +-- Active: exact-size quote ladder, optional token trades
        |
        v
SQLite append-only snapshots
        |
        v
Point-in-Time panel -> factor tests / markout / curve / capacity -> HTML report
```

每次采集都保存 `observed_at_ms`、endpoint、请求参数、HTTP/业务状态、延迟和原始 JSON。分析只能使用快照发生时已有的字段；当前快照不能回写过去。

## 采样预算

`BINANCE_WEB3_QPS` 是进程全局启动上限；默认新项目为 5，验证无误后再调高。批量接口每次最多 100 个 token。quote ladder 只在 Active Candidates 上运行。API 返回的 quote 约 30 秒有效，研究记录报价年龄，不把 quote 当作已成交价格。

## 研究验收门

```text
Statistical -> Economic -> Executable -> Scalable
```

任何 alpha 输出都必须同时报告样本量、缺失/失败样本、交易规模、流动性、冲击和成本边界；样本不足时显示 `INSUFFICIENT_DATA`，不填充漂亮数字。

