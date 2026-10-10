# shier-kefu（十二智能客服）

一个**RAG 驱动的智能客服系统**，面向企业内部客服场景：员工在前端提问，系统通过知识库检索 + 大模型生成答案；无法自动解答时自动生成工单流转给人工坐席，AI 坐席（Agent）辅助处理。

## 功能模块

| 模块 | 说明 |
|------|------|
| 用户认证 | 注册 / 登录 / JWT 鉴权（bcrypt + PyJWT） |
| 智能问答（QA） | 向量检索 + 意图识别 + 查询改写 + RAG（RRF 融合）+ LLM 生成 |
| 知识库（KB） | 文档上传、切分、入库（Ingest 任务），向量存储与检索 |
| 工单（Tickets） | 自动创建、状态机流转（服务层状态机驱动）、人工坐席处理 |
| AI 坐席 | 基于 LLM 工具调用的 Agent 辅助客服处理工单 |

前端页面：`LoginPage` / `EmployeePage`（员工提问）/ `AgentPage`（AI/人工坐席）/ `KnowledgePage`（知识库管理）。

## 技术栈

- **后端**：Python 3，FastAPI + SQLAlchemy（async / aiosqlite），按「路由 → 服务 → 模型」分层
- **自研框架 `pycore/`**：从 OpenManus 提取并泛化的异步后端框架——配置、日志、异常体系、插件系统、服务状态机、执行编排、LLM 集成（OpenAI / DeepSeek / Ollama、工具调用、Token 计数），详见 `pycore/docs/`
- **前端**：Vue 3 + TypeScript + Vite + Pinia + Vue Router
- **LLM**：通过 HTTP 集成大模型（`src/integrations/llm_http`），用于意图识别、查询改写、RAG 生成与 Agent

## 目录结构

```
shier-kefu/
├── backend/            # FastAPI 后端
│   ├── src/
│   │   ├── api/routes/ # auth / kb / tickets 路由
│   │   ├── services/   # auth_service / kb_service / rag_pipeline / ticket_service
│   │   ├── models/     # Pydantic 模型（auth / kb / ticket / ai）
│   │   ├── db/         # 异步数据库会话与 ORM
│   │   ├── integrations/ # LLM HTTP 客户端
│   │   └── core/       # 配置与错误定义
│   ├── config.toml     # 运行时配置
│   └── requirements.txt
├── frontend/           # Vue 3 前端（Vite）
├── pycore/             # 自研 Python 后端框架（含 docs/ 文档）
└── data/               # 运行数据
```

## 运行方式

后端：

```bash
cd backend
pip install -r requirements.txt
cp env.example .env   # 配置 LLM API 等
uvicorn src.main:app --reload
```

前端：

```bash
cd frontend
npm install
npm run dev
```

## RAG 问答链路（`backend/src/services/rag_pipeline.py`）

1. 向量检索召回相关 QA/知识片段
2. LLM 意图识别
3. 查询改写（多路召回）
4. RRF（Reciprocal Rank Fusion）融合排序
5. LLM 生成最终答案
6. 置信度不足时自动创建工单转人工
