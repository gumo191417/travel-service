# 旅游智能客服系统

面向在线旅游场景的智能客服。支持酒店、景点、机票、火车票、汽车票、接送服务的搜索与咨询，支持订单状态、行程信息、退款申请三类多轮任务，并提供闲聊兜底、意图澄清和转人工能力。

设计原则沿用电商客服项目：**大模型只负责理解与措辞，业务流转全部由确定性代码控制**。Planner 输出结构化计划，Validator 用规则校验，Flow 以 YAML 声明，所有槽位、任务状态和消息记录可持久化。

---

## 功能特性

| 能力 | 说明 |
|---|---|
| 三层路由 | 任务办理 / 知识咨询 / 闲聊，单轮只命中一个方向 |
| 任务式对话 | 槽位收集、条件跳转、任务切换 / 恢复 / 取消 |
| 六类产品搜索 | 酒店、景点、机票、火车票、汽车票、接送服务 |
| 订单与售后 | 订单状态、行程信息、退款申请 |
| 对象消息 | 用户发送订单卡片时自动补进当前任务的槽位 |
| 知识检索 | 酒店 / 景点 / 交通 / 订单 / 支付 / 退款 / 用户信息 |
| FAQ | YAML 维护问答，大模型从问题列表中挑选相关条目 |
| 意图澄清 | 计划无法执行时主动追问，而不是给出错误回复 |
| 转人工 | 创建转人工单、切换人工模式、客服接单 / 回复 / 关闭 |
| 状态持久化 | 整包对话状态以 JSON 存 MySQL，支持会话恢复与历史回溯 |
| 前端 | Vue 3 用户对话页 + 客服工作台，明暗主题 |

当前配置规模：

- 47 个业务槽位
- 6 条任务流程
- 16 个知识意图
- 12 个知识 Provider
- 9 个业务动作
- 14 条 FAQ

---

## 技术栈

**后端**

- Python 3.12
- FastAPI + Uvicorn
- SQLAlchemy 2.0（异步）+ aiomysql + MySQL 8
- Pydantic v2 / pydantic-settings
- LangChain（OpenAI 兼容接口）
- PyYAML

**前端**

- Vue 3（`<script setup>`）
- Vue Router 4
- Vite 6
- 原生 CSS 设计系统，无 UI 组件库

**外部依赖**

- travel-data：旅游业务数据服务，默认 `http://127.0.0.1:8000`，接口前缀 `/api/v1`
- LLM：任意 OpenAI 兼容接口

---

## 系统架构

```
用户 / 客服
    │  HTTP
    ▼
FastAPI（app/web）
    ├─ /api/chat/*     对话与会话管理
    ├─ /api/handoff/*  转人工
    └─ /               Vue SPA（static/）
    │
    ▼
DialogueService
    ├─ DialogueStateRepository ── MySQL（dialogue_states）
    └─ DialogueEngine
         ├─ TurnPlanner（LLM 出计划）
         ├─ TurnPlanValidator（确定性校验）
         ├─ TaskHandler
         │    ├─ CommandProcessor
         │    └─ FlowExecutor
         │         ├─ ActionRunner ── travel-data
         │         └─ ResponseRenderer（static / rephrase）
         ├─ KnowledgeHandler
         │    └─ Providers（业务 API / FAQ）
         ├─ ChitchatHandler
         └─ ClarifyResponder

转人工：HandoffService ── MySQL（handoff_requests）+ DialogueState
```

---

## 目录结构

```
travel-service/
├── app/
│   ├── domain/          领域模型：消息、状态、任务、命令、计划、Flow
│   ├── plan/            TurnPlanner + TurnPlanValidator
│   ├── task/            任务轨道
│   │   ├── command/     命令处理
│   │   ├── flow/        Flow 加载、执行、对象补槽
│   │   ├── action/      动作注册、执行与自定义动作
│   │   ├── lifecycle/   任务生命周期提示
│   │   └── response/    回复渲染
│   ├── knowledge/       知识意图、Provider、FAQ、应答
│   ├── handler/chitchat 闲聊轨道
│   ├── clarify/         澄清应答
│   ├── prompts/         提示词模板与历史拼接
│   ├── engine/          DialogueEngine 与组件装配
│   ├── service/         对话服务、转人工服务
│   ├── repository/      对话状态与转人工单读写
│   ├── models/          SQLAlchemy 模型
│   ├── web/             路由、Schema、依赖注入
│   ├── clients/         LLM、HTTP、数据库、travel-data、转人工入口
│   └── conf/            配置与城市映射
├── flow_config/
│   └── travel_flows.yml 槽位与流程定义
├── frontend/            Vue 3 + Vite 源码
│   └── src/
│       ├── views/       ChatView / AgentView
│       └── components/  MessageBubble / ChatComposer / StatusPill
├── static/              前端构建产物（FastAPI 托管）
├── main.py              FastAPI 入口
├── init_db.py           初始化数据表
├── requirements.txt
└── README.md
```

---

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 18+（仅前端开发或构建需要）
- MySQL 8
- 可用的 travel-data 服务
- OpenAI 兼容的 LLM 接口

### 1. 安装后端依赖

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

### 2. 配置环境变量

在项目根目录创建 `.env`：

```ini
# LLM
LLM_MODEL=qwen3.6-flash
LLM_BASE_URL=https://your-llm-endpoint/v1
LLM_API_KEY=sk-...

# travel-data 业务数据服务
TRAVEL_API_BASE_URL=http://127.0.0.1:8000

# 对话未显式传 user_id 时使用
DEMO_USER_ID=10001

# MySQL
DATABASE_URL=mysql+aiomysql://root:123456@127.0.0.1:3306/customer_service?charset=utf8mb4

# 服务
APP_HOST=0.0.0.0
APP_PORT=18084
```

> 18082 常被电商客服项目占用，本项目默认使用 18084。如与其它服务冲突，改 `APP_PORT` 并同步修改 `frontend/vite.config.js` 的代理端口。

### 3. 初始化数据库

数据库需要事先创建。建表脚本：

```bash
.venv\Scripts\python init_db.py
```

会创建 `dialogue_states` 和 `handoff_requests` 两张表。

### 4. 启动依赖服务

先启动 travel-data，确认 `http://127.0.0.1:8000` 可访问；再确认 LLM 接口可用。

### 5. 启动后端

```bash
.venv\Scripts\python main.py
```

访问：

- 用户对话：<http://127.0.0.1:18084/>
- 客服工作台：<http://127.0.0.1:18084/agent>
- Swagger：<http://127.0.0.1:18084/docs>
- 健康检查：`GET /api/health`

`main.py` 默认带 `reload=True`，仅适合开发环境。

### 6. 前端

**直接使用构建产物**

`static/` 已包含构建结果，启动后端即可访问，无需单独启动前端。

**开发模式**

```bash
cd frontend
npm install
npm run dev
```

访问 `http://127.0.0.1:5173`，`/api` 会代理到 `18084`。

**修改后重新构建**

```bash
cd frontend
npm run build
```

产物输出到 `static/`，后端无需重启。

---

## 配置项

| 变量 | 必填 | 说明 |
|---|---|---|
| `LLM_MODEL` | 是 | 模型名称 |
| `LLM_BASE_URL` | 是 | OpenAI 兼容接口地址 |
| `LLM_API_KEY` | 是 | 接口密钥 |
| `TRAVEL_API_BASE_URL` | 是 | travel-data 地址 |
| `DEMO_USER_ID` | 否 | 未传 `user_id` 时的默认业务用户，默认 10001 |
| `DATABASE_URL` | 是 | SQLAlchemy 异步 MySQL 连接串 |
| `APP_HOST` | 是 | 监听地址 |
| `APP_PORT` | 是 | 监听端口 |

---

## 前端说明

### 页面

**用户对话 `/`**

- 左侧：快速开始、当前订单卡片
- 中间：消息列表、输入框、状态标识
- 右侧：会话状态（模式、活动任务、步骤、槽位），可隐藏
- 支持新会话、刷新、对象卡片发送
- 人工接管后自动切换为 3 秒轮询，客服消息以琥珀色气泡展示

**客服工作台 `/agent`**

- 左侧：转人工队列，支持待接入 / 处理中 / 已关闭 / 全部筛选
- 右侧：会话详情、客服名称、接单 / 关闭、回复输入框
- 消息按客服视角排列：用户消息在左、客服自己的回复在右
- 队列 5 秒轮询，会话 3 秒轮询

### 设计

视觉参考 ElevenLabs UI 的设计语言，使用纯 CSS 实现：

- 近黑主色 + 中性灰阶，细边框与克制阴影
- 16–18px 大圆角面板，胶囊状态标签
- 用户消息深色、机器人消息白底描边、人工客服琥珀色
- 明暗双主题，主题选择保存在 localStorage

### 开发与构建

- 开发：`npm run dev`（5173，代理 `/api` 到 18084）
- 构建：`npm run build`（输出到 `../static`）

---

## 接口文档

### 对话

#### `POST /api/chat`

文本消息：

```json
{
  "sender_id": "demo-001",
  "user_id": 10001,
  "text": "三亚有哪些五星酒店"
}
```

对象消息：

```json
{
  "sender_id": "demo-001",
  "user_id": 10001,
  "object": {
    "type": "order",
    "id": "TR_DEMO_0001",
    "title": "三亚酒店订单"
  }
}
```

响应：

```json
{
  "sender_id": "demo-001",
  "message_id": "…",
  "messages": [
    { "text": "好的，我们先处理产品搜索。", "object": null }
  ],
  "human_mode": false
}
```

`human_mode=true` 表示人工接管中，此时机器人不生成回复，`messages` 通常为空。

#### `GET /api/chat/history?sender_id=demo-001`

按会话、轮次展开的历史消息。`role` 取值：

- `user`：用户
- `bot`：机器人
- `agent`：人工客服

响应包含 `human_mode`。

#### `POST /api/chat/sessions`

```json
{ "sender_id": "demo-001", "user_id": 10001 }
```

关闭当前会话、清理运行态（聚焦对象、活动任务、人工模式），开启新会话。

#### `GET /api/chat/state?sender_id=demo-001`

返回：

```json
{
  "sender_id": "demo-001",
  "session_id": "…",
  "started_at": 1762…,
  "active_task": {
    "task_id": "…",
    "flow_id": "product_search",
    "step_id": "hotel_check_out",
    "slots": { "city": "三亚" }
  },
  "paused_tasks": [],
  "focused_object": null,
  "slots": { "city": "三亚" },
  "human_mode": false,
  "handoff_no": null
}
```

### 转人工

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/handoff/requests?status=pending` | 查询转人工单 |
| POST | `/api/handoff/requests/{handoff_no}/takeover` | 接单，body `{"agent_name":"小王"}` |
| POST | `/api/handoff/requests/{handoff_no}/reply` | 回复，body `{"text":"…","agent_name":"小王"}` |
| POST | `/api/handoff/requests/{handoff_no}/close` | 关闭，机器人恢复 |

错误码：单号不存在 404，已关闭仍回复 409，其它业务错误 400。

转人工流程：

1. 用户说“转人工”，Planner 进入 `human_handoff` 流程
2. 动作创建转人工单，回复工单号，并把会话切到人工模式
3. 人工模式下用户消息照常入库，机器人不再自动回复
4. 客服 `reply` 后，消息以 `role=agent` 追加到当前会话
5. 用户前端轮询 `/api/chat/history` 看到回复
6. 客服 `close` 后 `human_mode` 清除，机器人恢复

演示环境不做鉴权。

### 系统

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查 |
| GET | `/docs` | Swagger UI |
| GET | `/openapi.json` | OpenAPI 描述 |

---

## 业务流程

### 三条轨道

1. **任务**：执行 YAML 中定义的 Flow，收集槽位并调用业务动作
2. **知识**：按意图并发调用 Provider，由 LLM 组织回复
3. **闲聊**：不查业务数据，只根据上下文自然应答

Planner 只输出计划，Validator 负责单方向、Flow、Command、槽位、意图和对象依赖的校验；校验失败统一交给 ClarifyResponder。

### 任务流程

| Flow | 说明 |
|---|---|
| `onboarding` | 欢迎语与能力介绍 |
| `product_search` | 按产品类型路由到酒店、景点、交通、接送的搜索步骤 |
| `order_status_query` | 订单号 → 查询订单 → 状态回复 |
| `travel_info_query` | 订单号 → 查询订单 → 行程摘要 |
| `refund_request` | 订单号 → 明细选择 → 退款原因 → 退款类型 → 提交退款 |
| `human_handoff` | 创建转人工单并进入人工模式 |

流程支持 `start / collect / action / response / end` 五种步骤和 `if / else` 条件跳转。

### 对象消息

用户在页面上点选订单卡片时，引擎会：

1. 写入 `focused_object`
2. 检查当前活动任务的 `collect` 步骤是否声明了 `object_type / object_field`
3. 匹配则补槽并继续流程，否则发起“你想对这个对象做什么”的澄清

### 转人工

- 转人工单存 `handoff_requests` 表
- 会话状态新增 `human_mode`、`handoff_no`
- 人工回复以 `BotMessage(role="agent")` 追加到用户当前会话
- 客服回复写入时对 `dialogue_states` 行加锁，减少与用户消息的覆盖冲突

---

## 知识库

### 知识意图（16）

- 产品：`hotel_info`、`scenic_info`、`flight_info`、`train_info`、`bus_info`、`transfer_info`
- 订单：`order_info`、`payment_info`、`refund_status`
- 用户：`user_info`、`member_info`
- 政策：`refund_policy`、`change_policy`、`booking_rule`、`travel_notice`、`general_travel`

### Provider（12）

`api.hotel`、`api.scenic`、`api.flight`、`api.train`、`api.bus`、`api.transfer`、`api.order`、`api.payment`、`api.user`、`api.refund`、`faq.default`、`rag.default`（占位，未接入意图）。

### FAQ

- 数据文件：`app/knowledge/faq_data/travel_faq.yml`（当前 14 条）
- 匹配方式：把问题列表交给大模型，返回相关 FAQ ID
- 最多返回 3 条；无命中、对象消息或模型异常时返回空片段

---

## 数据模型

### `dialogue_states`

| 字段 | 类型 | 说明 |
|---|---|---|
| `sender_id` | VARCHAR(255) PK | 会话键 |
| `state_json` | LONGTEXT | 完整 DialogueState JSON |

`state_json` 结构：

```
DialogueState
├─ sender_id
├─ user_id
├─ shared_state
│   ├─ focused_object
│   ├─ sessions[] → turns[] → user_message / bot_messages[]
│   ├─ human_mode
│   └─ handoff_no
└─ task_state
    ├─ active_task（flow_id / step_id / slots / task_id）
    └─ paused[]
```

### `handoff_requests`

| 字段 | 说明 |
|---|---|
| `handoff_no` | 转人工单号，唯一 |
| `sender_id` / `user_id` / `session_id` | 关联信息 |
| `reason` | 转人工原因 |
| `status` | `pending / taken / closed` |
| `agent_name` | 接单客服 |
| `created_at / taken_at / closed_at` | 时间 |

---

## 关键设计

1. **计划与执行分离**
   Planner 只输出 JSON，Validator 用确定性规则判断能否执行，任务状态只由 CommandProcessor 修改。

2. **Flow 配置化**
   新增业务流程只需要在 `flow_config/travel_flows.yml` 中声明槽位和步骤，不需要改核心代码。

3. **动作统一入口**
   所有 travel-data 调用走 `app/clients/travel_api.py`，动作和知识 Provider 共用超时、错误文案和订单号解析。

4. **整包状态持久化**
   `sender_id` 是会话键，`user_id` 是业务身份；每次请求加载状态、执行、保存。

5. **单轮异常兜底**
   `DialogueEngine` 捕获单轮异常，记录日志并返回兜底话术，不中断后续对话。

6. **转人工与机器人隔离**
   人工模式下引擎跳过 Planner 和三条轨道，用户消息只入库，由客服通过接口接管。

---

## 演示场景

| 场景 | 输入示例 |
|---|---|
| 酒店搜索 | 三亚有哪些五星酒店？ |
| 景点搜索 | 上海有哪些 4A 景点？ |
| 机票 / 火车 / 汽车 | 明天从上海到北京的高铁 |
| 接送服务 | 三亚机场接送 |
| 订单状态 | 帮我查订单 TR_DEMO_0001 |
| 行程信息 | 这个订单哪天入住？ |
| 退款申请 | 我要退款 |
| 政策咨询 | 退款政策是什么？ |
| 任务切换 | 退款进行中再查订单，然后恢复退款 |
| 对象补槽 | 先开始查订单，再发送订单卡片 |
| 转人工 | 我要转人工客服 |

---

## 验证方式

### 健康检查

```bash
curl http://127.0.0.1:18084/api/health
```

### 对话闭环

```bash
curl -X POST http://127.0.0.1:18084/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"sender_id\":\"demo-001\",\"user_id\":10001,\"text\":\"三亚有哪些五星酒店？\"}"
```

### 会话状态

```bash
curl "http://127.0.0.1:18084/api/chat/state?sender_id=demo-001"
```

### 转人工

```bash
curl "http://127.0.0.1:18084/api/handoff/requests?status=pending"
```

```bash
curl -X POST http://127.0.0.1:18084/api/handoff/requests/HO.../reply \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"你好，我是客服小王\",\"agent_name\":\"小王\"}"
```

---

## 常见问题

### 接口返回 500

1. 检查 `DATABASE_URL` 和密码是否正确
2. **修改 `.env` 后必须重启进程**，pydantic-settings 只在启动时读取一次
3. 确认已执行 `init_db.py`

### 启动时报 `ValidationError`

`.env` 缺少必填项，或存在旧的 `COMMERCE_API_BASE_URL` 等多余字段。

### 端口被占用

18082 常被电商项目占用；本项目使用 18084。检查占用：

```powershell
Get-NetTCPConnection -LocalPort 18084 -State Listen
```

### 前端 500 / 代理失败

1. 确认后端已启动在 `18084`
2. 确认 `frontend/vite.config.js` 的代理端口与 `.env` 一致
3. 修改代理配置后 Vite 会自动重启，必要时重新 `npm run dev`

### 静态页面没有更新

执行 `npm run build`，Vite 会把新产物写入 `static/`。

### 知识检索或回复很慢

Planner、回复改写和 FAQ 选择都会调用 LLM，属于正常时延；可先在提示词里减少改写场景。

---

## 已知限制

- 未实现 SSE 流式响应
- 转人工接口未做鉴权，仅用于演示
- 用户消息与客服回复都保存在同一个 `state_json`；客服侧已加行锁，用户侧未加乐观锁，极高并发下仍可能覆盖
- RAG 知识库未实现，`rag.default` 保留但未被任何意图引用
- 工单提交未实现，只提供转人工单
- 条件表达式使用受限 `eval` 沙箱，槽位中不要放不可 JSON 序列化的对象
- 城市映射是静态表（`app/conf/areas.py`），需与 travel-data 的 `areas` 数据核对

## 后续可以做的

- SSE 流式输出
- RAG 知识库与文档上传
- 转人工工作台鉴权与坐席分配
- 消息独立建表，支持审计与全文检索
- 对话处理轨迹与耗时监控
- 自动化测试入库（当前为开发期 MockTransport 冒烟测试）