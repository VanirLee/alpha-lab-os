# AlphaLabOS

面向量化研究员的链上市场研究实验室。项目把 Binance Web3 API 作为只读的数据扫描与 enrichment 来源，围绕 Point-in-Time 数据、可复现计算和明确的证据边界，研究链上市场信息如何传导到后续价格与流动性结果。

这个仓库是研究代码和可复现样例，不是交易机器人、钱包管理器或收益承诺。默认不下单、不转账、不签名、不授权钱包，也不调用任何 write endpoint。

## 研究内容

当前代码按四类研究问题组织：

1. CEX–DEX microstructure：报价、路线、quote freshness 和可承载规模边界。
2. Wallet / flow：交易流、成交后 markout 与参与者行为；商业标签只作为待验证字段。
3. Cross-sectional factors：momentum、主动买卖、流动性、持仓结构与未来收益。
4. Lifecycle / events：token 状态、创建/开发者信息与事件窗口。

项目当前提供的是小规模真实只读 smoke run 与离线 synthetic demo。任何结果都应结合覆盖率、失败原因、时间切分和样本外验证阅读，不应把短样本相关性直接称为 alpha。

## 目录导航

```text
alpha-lab-os/
├── src/alpha_lab_os/   API client、限流、采集、SQLite、特征、统计与 dashboard
├── configs/            显式 token universe 与采样配置
├── docs/               架构、数据边界与研究说明
├── tests/              离线单元测试
├── data/               demo / smoke SQLite 数据库样例
├── artifacts/          demo 与 smoke HTML 研究输出
├── Makefile            常用命令入口
├── pyproject.toml      Python 包元数据
└── .env.example        不含真实凭据的配置模板
```

GitHub 页面中的源码、测试、文档和结果文件均可直接打开；如果只想快速了解项目，建议按 `README → docs/architecture.md → src/alpha_lab_os/cli.py → tests/` 的顺序阅读。

## 从全新环境运行

Python 3.9 及以上即可。项目目前依赖标准库完成核心流程；若要运行额外的本地分析工具，再按实际环境安装对应依赖。

```bash
git clone https://github.com/VanirLee/alpha-lab-os.git
cd alpha-lab-os

python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .

# 安全检查、离线 demo 和测试
PYTHONPATH=src python -m alpha_lab_os doctor
PYTHONPATH=src python -m alpha_lab_os demo --db data/demo.db --html artifacts/demo.html
PYTHONPATH=src python -m unittest discover -s tests -v
```

`demo` 使用明确标记为 `synthetic` 的离线样本，验证数据库、特征、统计和 HTML dashboard 的完整链路；它不代表真实市场表现。

## 真实 Binance Web3 只读采集

公开仓库只提供模板，不包含 API key、secret 或个人环境路径。复制 `.env.example` 为本地私有配置，或在 shell 中设置相应变量；私有文件不要提交。

先查看采集计划：

```bash
PYTHONPATH=src python -m alpha_lab_os collect \
  --config configs/universe.json \
  --db data/alpha_lab.db \
  --html artifacts/alpha-latest.html \
  --dry-run
```

确认参数后再运行真实采集：

```bash
PYTHONPATH=src python -m alpha_lab_os collect \
  --config configs/universe.json \
  --db data/alpha_lab.db \
  --html artifacts/alpha-latest.html
```

重新分析已有数据库：

```bash
PYTHONPATH=src python -m alpha_lab_os analyze \
  --db data/alpha_lab.db \
  --html artifacts/analysis.html
```

真实采集只允许市场、数据和报价读取接口。遇到限流、权限失败、空路由、缺字段或样本不足时，应保留失败状态，不能用未来数据或未经声明的 proxy 静默替换。

## 数据与 Point-in-Time 边界

- 采集时间、事件时间和分析时间分开记录；不能用后来才知道的分类或最终结果构造历史特征。
- 资产和钱包标识应保留链、合约或地址上下文，不能只依赖 symbol。
- `observed_at` 代表本地看到数据的时间；无法确认历史可得性时，结果只能作为当前观测或 smoke evidence。
- `synthetic`、`real_api` 和 `unsupported` 证据必须区分。
- 该项目不实现 mempool/MEV、完整钱包图谱、历史全量回放或可执行套利证明；这些需要额外的 RPC、indexer、raw logs、traces、深度/成交执行数据。

## 安全边界

凭据只应从本地环境或私有配置读取，代码不会把 key/secret 打印到日志、HTML 或报告。仓库中的 `.env.example` 只说明变量形状；`.gitignore` 会忽略 `.env`、本地数据库、缓存和编译产物。

项目结果仅用于研究与工程验证，不构成投资建议，也不保证任何可执行交易收益。
