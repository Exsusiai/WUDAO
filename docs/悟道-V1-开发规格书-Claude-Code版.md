# 悟道 V1 开发规格书（Claude Code 可直接开工版）

> 目标：给 Claude Code 一份可直接进入开发的 V1 规格书。
> 
> V1 定位不是量化研究平台，不是回测实验室，也不是全自动交易系统。
> 
> **悟道 V1 = 面向 Jason 本人的、本地优先、跨平台、手动 / 半手动交易执行工作台。**

---

## 1. V1 产品目标

V1 只解决一件事：

**把真人交易的执行、风控、仓位管理、记录、复盘收进一个统一系统。**

也就是说，第一版必须优先满足：
- 连接交易所
- 连接 TradingView
- 接收信号并转成待执行意图
- 做基础风控与纪律检查
- 支持止盈止损 / 仓位管理
- 记录订单、成交、持仓变化
- 写入本地数据库
- 同步复盘摘要到 Notion

V1 不追求：
- 回测平台
- 参数实验管理
- 多策略绩效实验室
- 复杂量化研究基础设施
- AI 自动上策略
- 多用户协作

---

## 2. V1 范围定义

## 2.1 In Scope（必须做）

### A. 交易所连接
V1 必须支持至少 **1 个主交易所** 的完整接入。

支持能力：
- 查询账户余额
- 查询持仓
- 查询未成交订单
- 查询历史订单 / 成交
- 市价下单
- 限价下单
- 撤单
- 查询订单状态

要求：
- 使用统一适配器接口设计
- 首期可只实现一个交易所适配器
- 如果目标交易所支持 testnet / sandbox，则必须支持

建议实现：
- Python `ccxt`
- 首期使用 REST + polling
- WebSocket 不作为 V1 阻塞项

---

### B. TradingView Webhook 接入
V1 必须支持 TradingView 发信号进入系统。

支持能力：
- 提供 webhook endpoint
- 解析固定 payload schema
- 将 webhook 转换为系统内部 `Signal` / `OrderIntent`
- 标记来源、symbol、方向、策略标签、备注
- 写入待处理队列
- 进入风控 / 纪律检查流程
- 支持人工确认执行

关键要求：
- V1 只支持 **一种统一的 webhook schema**
- 不做多格式兼容地狱
- Claude Code 需要同时提供示例 TradingView alert message 模板

---

### C. 风控、止盈止损、仓位管理
这是 V1 的产品核心，不是附属功能。

V1 必须支持：

#### 止损 / 止盈策略
- 固定止损（fixed stop loss）
- 固定止盈（fixed take profit）
- 分批止盈（ladder take profit）
- 追踪止损（trailing stop）
- 盈利达到阈值后移动保本（break-even move）
- 手动一键平仓 / 减仓

#### 仓位管理
- 单笔最大仓位限制
- 单笔最大风险限制
- 总体风险暴露显示
- 同方向风险限制
- 根据账户净值和止损距离给出建议仓位

#### 风控 / 纪律检查
- 没有止损，不允许提交订单
- 超过单笔风险限制，不允许提交订单
- 超过单笔最大仓位，不允许提交订单
- 达到当日最大亏损后，不允许开新仓
- 支持可配置的冷静期（可选，但建议做）

说明：
- V1 不做复杂规则 DSL
- V1 做结构化规则配置即可

---

### D. 账户 / 持仓 / 订单总览
V1 必须有一个真人每天愿意打开的 Dashboard。

首页至少展示：
- 当前账户净值
- 可用余额
- 当前持仓
- 未成交订单
- 今日已实现盈亏
- 今日未实现盈亏
- 总风险暴露
- 待确认的 `OrderIntent`
- 风控告警 / 纪律告警
- 最近 TradingView 信号

目标：
- Jason 打开后 10 秒内知道当前系统状态

---

### E. 交易记录与复盘
V1 必须有交易记录闭环。

支持能力：
- 自动记录订单与成交
- 自动关联持仓变化
- 平仓后生成 trade record
- 手动补充交易理由、策略标签、备注、情绪
- 支持按时间 / 标的 / 策略标签查询历史
- 展示单笔交易完整链路：
  - signal
  - order intent
  - order
  - fill
  - position change
  - journal entry

关键原则：
- **数据库是唯一主数据源**
- Notion 只是同步目标，不是交易系统主库

---

### F. Notion 同步
V1 支持把复盘和交易摘要同步到 Notion。

同步内容建议：
- 已平仓交易摘要
- 每日复盘摘要
- 交易日志 / Journal Entry
- 策略标签 / 备注信息

V1 约束：
- Notion 只做单向同步（system -> notion）
- 不做双向同步
- 不允许 Notion 反向驱动订单状态
- 不允许 Notion 反向驱动风控参数

---

### G. 通知与告警
V1 支持基础告警与通知。

通知渠道：
- 应用内通知
- Telegram

通知事件：
- TradingView 信号进入
- 新待确认订单意图
- 下单成功 / 失败
- 止损 / 止盈触发
- 风险超限
- 撤单成功 / 失败

---

### H. 模式切换：Live / Sandbox
虽然 V1 不做完整 Shadow 平台，但必须支持最小测试模式。

必须支持：
- `sandbox` 模式
- `live` 模式
- UI 明确显示当前模式
- 配置级切换
- 日志中必须记录当前模式

要求：
- 禁止让真钱账户承担系统联调测试职责

---

## 2.2 Out of Scope（V1 明确不做）

以下能力不进入 V1：
- 回测平台
- 参数实验管理
- Walk-forward / cross-validation
- 因子研究系统
- 多策略绩效对比中心
- AI 自动生成并上线策略
- 多用户权限体系
- 原生桌面端封装
- 多交易所同时完整支持
- 复杂自动化执行编排
- 高级组合管理 / 多账户资金分配引擎

这些内容进入 V2 或更后续版本。

---

## 3. 用户与使用方式

V1 仅面向单用户 Jason。

使用方式：
- 本地启动 Web App
- 浏览器访问本地 UI
- 通过 UI 查看账户、持仓、订单、Journal
- 通过 TradingView webhook 推送信号
- 通过系统确认并执行订单
- 通过 Notion 查看同步后的可读复盘结果

---

## 4. 运行平台要求

V1 必须在以下平台可运行：
- macOS
- Ubuntu

要求：
- 不依赖仅 Linux 可用的实现
- 不依赖仅 macOS 可用的实现
- 所有路径处理使用跨平台方式
- 所有本地数据目录使用平台标准目录定位

建议：
- Python 使用 `platformdirs`
- Node/前端避免依赖平台专属脚本
- 提供统一 `make` 或 `just` 命令（若可行）
- 提供 `scripts/dev` / `scripts/start` 跨平台启动脚本

---

## 5. 技术架构要求

V1 推荐技术栈：

### 前端
- Next.js
- TypeScript
- Tailwind CSS
- shadcn/ui

### 后端
- FastAPI
- Pydantic / SQLModel 或 SQLAlchemy

### 数据库
- SQLite

### 交易所适配
- `ccxt`

### 定时任务
- APScheduler

### Notion
- 官方 API（SDK 或直接 HTTP）

### 通知
- Telegram Bot API / 现有消息通道封装

架构形态：
- 本地优先 Web App
- 前后端分离
- API + Worker 分职责
- 单机可运行

---

## 6. 系统模块划分

V1 需要以下模块：

### 6.1 Web App
负责：
- Dashboard
- Positions
- Orders
- Pending Intents
- Journal
- Settings
- Alerts

### 6.2 API Service
负责：
- 账户信息 API
- 订单 API
- Webhook API
- Journal API
- Settings API
- Notion sync trigger API

### 6.3 Worker / Scheduler
负责：
- 轮询订单状态
- 轮询账户状态
- 检查触发止盈止损
- 推送告警
- 执行 Notion 同步任务

### 6.4 Exchange Adapter
负责：
- 交易所统一接口
- 下单 / 撤单 / 查询

### 6.5 Risk Engine
负责：
- 仓位建议
- 单笔风险计算
- 止损止盈规则计算
- 风控检查

### 6.6 Journal / Review Service
负责：
- 交易记录聚合
- 平仓结果沉淀
- Journal Entry 生成
- Notion 同步数据整形

---

## 7. 核心数据模型

V1 必须至少定义以下对象。

### 7.1 ExchangeAccount
字段建议：
- `id`
- `name`
- `exchange`
- `mode` (`live` | `sandbox`)
- `base_currency`
- `status`
- `created_at`
- `updated_at`

### 7.2 TradingViewSignal
字段建议：
- `id`
- `source` (`tradingview`)
- `symbol`
- `side` (`buy` | `sell`)
- `timeframe`
- `strategy_tag`
- `payload_raw`
- `note`
- `received_at`

### 7.3 OrderIntent
字段建议：
- `id`
- `signal_id` (nullable)
- `account_id`
- `symbol`
- `side`
- `order_type`
- `quantity`
- `intended_entry_price`
- `stop_loss`
- `take_profit_mode`
- `take_profit_config_json`
- `risk_amount`
- `risk_percent`
- `status` (`pending_review` | `approved` | `rejected` | `submitted` | `cancelled`)
- `review_note`
- `created_at`
- `updated_at`

### 7.4 Order
字段建议：
- `id`
- `intent_id`
- `exchange_order_id`
- `symbol`
- `side`
- `order_type`
- `price`
- `quantity`
- `status`
- `submitted_at`
- `updated_at`

### 7.5 Fill
字段建议：
- `id`
- `order_id`
- `exchange_fill_id`
- `price`
- `quantity`
- `fee`
- `fee_currency`
- `filled_at`

### 7.6 Position
字段建议：
- `id`
- `account_id`
- `symbol`
- `side`
- `quantity`
- `avg_entry_price`
- `mark_price`
- `unrealized_pnl`
- `realized_pnl`
- `risk_exposure`
- `updated_at`

### 7.7 RiskRule
字段建议：
- `id`
- `rule_type`
- `enabled`
- `config_json`
- `created_at`
- `updated_at`

规则类型至少支持：
- `max_position_size`
- `max_risk_per_trade`
- `max_daily_loss`
- `require_stop_loss`
- `cooldown_period`

### 7.8 TradeJournalEntry
字段建议：
- `id`
- `position_id` (nullable)
- `symbol`
- `strategy_tag`
- `entry_reason`
- `exit_reason`
- `pre_trade_plan`
- `emotion_note`
- `mistake_tags_json`
- `summary`
- `status` (`open` | `closed`)
- `opened_at`
- `closed_at`

### 7.9 NotionSyncJob
字段建议：
- `id`
- `target_type`
- `target_id`
- `status`
- `last_error`
- `scheduled_at`
- `processed_at`

### 7.10 AppSettings
字段建议：
- `id`
- `current_mode` (`live` | `sandbox`)
- `default_account_id`
- `telegram_notifications_enabled`
- `notion_sync_enabled`
- `created_at`
- `updated_at`

---

## 8. Webhook Schema（V1 固定格式）

TradingView -> 悟道 的 webhook payload 先固定为以下 JSON：

```json
{
  "source": "tradingview",
  "symbol": "BTC/USDT",
  "side": "buy",
  "timeframe": "1h",
  "strategy_tag": "breakout-v1",
  "note": "optional text",
  "entry_price": 65000,
  "stop_loss": 63500,
  "risk_percent": 1.0
}
```

字段要求：
- `source`: 必须为 `tradingview`
- `symbol`: 必填
- `side`: `buy` 或 `sell`
- `timeframe`: 必填
- `strategy_tag`: 必填
- `entry_price`: 可选，但建议传
- `stop_loss`: 可选，但 V1 风控如果启用了 require stop，则缺失时拒绝进入可执行状态
- `risk_percent`: 可选

Claude Code 需要：
- 实现 payload validation
- 返回明确错误信息
- 提供 TradingView alert 模板示例

---

## 9. 核心业务流程

## 9.1 手动下单流程
1. 用户在 UI 创建 `OrderIntent`
2. 输入 symbol / side / qty / stop / TP 配置
3. Risk Engine 校验
4. 若通过，则进入 `pending_review`
5. 用户确认后提交到交易所
6. 生成 `Order`
7. 同步订单状态与成交
8. 更新 `Position`
9. 写入 `TradeJournalEntry`

## 9.2 TradingView 信号流程
1. TradingView webhook 到达 API
2. 生成 `TradingViewSignal`
3. 转换为 `OrderIntent`
4. Risk Engine 校验
5. 若通过，则进入待确认列表
6. 用户确认后提交交易所
7. 后续同步订单、成交、持仓、Journal

## 9.3 平仓与 Journal 流程
1. 用户平仓或止盈止损触发
2. 订单执行并生成成交
3. 系统更新持仓状态
4. 若仓位关闭，则生成 / 完成 `TradeJournalEntry`
5. 用户可补充备注、复盘、情绪
6. 系统把摘要加入 Notion 同步队列

## 9.4 Notion 同步流程
1. `TradeJournalEntry` 或日终摘要进入 `NotionSyncJob`
2. Worker 执行同步
3. 成功则标记 `processed`
4. 失败则记录错误并支持重试

---

## 10. API 需求

V1 至少实现以下 API。

### 10.1 Health / App
- `GET /api/health`
- `GET /api/settings`
- `PUT /api/settings`

### 10.2 Exchange / Account
- `GET /api/accounts`
- `GET /api/accounts/{id}`
- `GET /api/accounts/{id}/balances`
- `GET /api/accounts/{id}/positions`
- `GET /api/accounts/{id}/orders`

### 10.3 TradingView
- `POST /api/webhooks/tradingview`
- `GET /api/signals`
- `GET /api/signals/{id}`

### 10.4 Order Intents / Orders
- `GET /api/order-intents`
- `POST /api/order-intents`
- `POST /api/order-intents/{id}/review`
- `POST /api/order-intents/{id}/submit`
- `POST /api/orders/{id}/cancel`
- `GET /api/orders`
- `GET /api/orders/{id}`

### 10.5 Risk / Rules
- `GET /api/risk/rules`
- `PUT /api/risk/rules`
- `POST /api/risk/check`
- `POST /api/risk/position-size-suggestion`

### 10.6 Journal / Review
- `GET /api/journal`
- `GET /api/journal/{id}`
- `POST /api/journal/{id}/notes`
- `GET /api/trades/history`

### 10.7 Notion Sync
- `GET /api/integrations/notion/status`
- `POST /api/integrations/notion/sync/{journalId}`
- `GET /api/integrations/notion/jobs`

### 10.8 Alerts
- `GET /api/alerts`
- `POST /api/alerts/test`

---

## 11. UI 页面要求

V1 至少包含以下页面：

### 11.1 Dashboard
展示：
- 当前模式（live / sandbox）
- 账户净值
- 余额
- 当前持仓
- 未成交订单
- 待确认 OrderIntent
- 今日盈亏
- 风险告警
- 最近 TradingView 信号

### 11.2 Positions
展示：
- 当前持仓列表
- 平均成本
- 当前盈亏
- 风险暴露
- 止损 / 止盈设置
- 快捷减仓 / 平仓动作

### 11.3 Orders
展示：
- 未成交订单
- 历史订单
- 成交详情
- 撤单操作

### 11.4 Pending Intents
展示：
- 待确认信号
- 风控检查结果
- 提交执行按钮
- 拒绝按钮
- review note

### 11.5 Journal
展示：
- 历史 trade records
- 单笔详情
- 备注与情绪补充
- 策略标签过滤
- Notion 同步状态

### 11.6 Settings
展示：
- 账户配置
- 模式切换
- 风控配置
- Notion 配置
- Telegram 配置

---

## 12. 实现约束

Claude Code 在实现时必须遵守：

1. **数据库是主数据源**
   - Notion 绝不能成为交易系统 source of truth

2. **先支持一个交易所，抽象好接口即可**
   - 不要为了“将来支持很多”把今天写成一坨抽象垃圾

3. **不要为了未来回测平台污染 V1 代码**
   - V1 只保留必要扩展点
   - 不提前实现 V2 的复杂概念

4. **所有关键动作都要记录日志**
   - webhook 接收
   - 风控拒绝
   - 人工确认
   - 下单成功 / 失败
   - 止盈止损触发
   - Notion 同步成功 / 失败

5. **必须兼容 macOS 与 Ubuntu**
   - 不写平台专属硬编码路径
   - 不依赖 systemd 才能运行
   - 本地开发和单机部署都必须成立

6. **模式显示必须明显**
   - UI 顶部明确显示当前为 `LIVE` 或 `SANDBOX`
   - 避免误操作

---

## 13. 建议目录结构

```text
wudao/
├── apps/
│   └── web/
├── services/
│   ├── api/
│   └── worker/
├── packages/
│   └── schemas/
├── python/
│   ├── exchange/
│   ├── risk/
│   ├── journal/
│   ├── notion_sync/
│   ├── notifications/
│   └── core/
├── infra/
│   ├── db/
│   └── scripts/
└── docs/
```

---

## 14. 开发里程碑

## Milestone 0：工程骨架
目标：项目可启动，可开发，可在 macOS / Ubuntu 运行。

交付：
- web + api + db 跑通
- 基础 schema
- 配置系统
- `live / sandbox` 模式切换
- 日志系统
- 基础 README

验收标准：
- 本地一条命令启动开发环境
- macOS / Ubuntu 均可跑通

---

## Milestone 1：交易所接入
目标：完成一个主交易所的账户 / 订单 / 持仓能力。

交付：
- 账户查询
- 持仓查询
- 下单 / 撤单
- 订单同步
- 成交同步

验收标准：
- sandbox 下可以完成真实联调
- UI 可以看到账户、订单、持仓

---

## Milestone 2：TradingView Webhook
目标：打通 TV -> OrderIntent。

交付：
- webhook endpoint
- payload validation
- signal 持久化
- order intent 自动生成
- 待确认列表页面

验收标准：
- 从 TradingView 发一个测试 alert 能在 UI 中看到待处理信号

---

## Milestone 3：风控与执行流
目标：完成真人可用的执行前检查与基础管理。

交付：
- 风控规则配置
- 仓位建议
- 固定 SL / TP
- ladder TP
- trailing stop
- break-even move
- review -> submit flow

验收标准：
- 没止损无法提交
- 超风控限制无法提交
- 通过 review 后可下单

---

## Milestone 4：Dashboard / Orders / Positions UI
目标：把系统变成可日常打开的工具。

交付：
- Dashboard
- Positions
- Orders
- Alerts
- Pending Intents

验收标准：
- 打开系统后 10 秒内能理解当前状态

---

## Milestone 5：Journal + Notion
目标：完成交易记录与复盘闭环。

交付：
- Trade journal
- 复盘备注
- 历史查询
- Notion 单向同步
- 同步任务状态追踪

验收标准：
- 一笔完整交易从信号到平仓后可追溯
- 关闭后的交易摘要可同步到 Notion

---

## 15. 验收标准（V1 Overall）

V1 完成的标志：

1. 能在 macOS 和 Ubuntu 本地运行
2. 能连接至少一个主交易所
3. 能接收 TradingView webhook
4. 能将 webhook 转成待确认订单意图
5. 能在风控检查后人工确认下单
6. 能查看账户、持仓、订单、成交
7. 能记录交易与复盘内容
8. 能同步摘要到 Notion
9. 能在 sandbox 模式安全联调
10. UI 明确，不像一坨开发者后台

---

## 16. 给 Claude Code 的明确实施建议

1. 先做可运行最小闭环，不要一开始追求完美抽象。
2. 先支持一个交易所，再谈多交易所。
3. 先做本地优先，不做复杂云部署。
4. 先做单用户，不做权限系统。
5. 先把真人执行链条做通，再考虑量化研究链条。
6. 所有超出 V1 范围的功能，统一记录在 `Future Work`，不要偷渡进当前里程碑。

---

## 17. 一句话总结

**悟道 V1 不是量化研究平台，而是 Jason 的真人交易执行工作台。**

先把：
- 交易所连接
- TradingView 信号接入
- 风控与仓位管理
- 交易记录与 Notion 复盘

这四件事做扎实，再谈 V2 的研究、评估、回测与策略平台。
