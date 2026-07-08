# 🏗️ Koan (Unite DeFi) Infrastructure Documentation

## 📌 Purpose
This document describes the production-like infrastructure for Koan, with **code-accurate references** to services, ports, APIs, and configuration. It also **aligns directly with the Architecture Document template**, providing descriptions for required diagrams: **use case, class, DFD, component, sequence, and deployment**.

**Sources used**
- Codebase (`frontend/`, `backend/`, `agents/`)
- `backend/env.example`
- `frontend/env.local.example`
- `backend/Dockerfile`
- `README.md`

---

## 🌐 System Topology (3-Tier Services)
**Koan = Frontend + Backend + Agents**, wired through REST APIs.

```
[Browser]
   ↓ HTTP
[Frontend :3000]  ─────→  [Agents API :8000]
   ↓ HTTP                         ↓ HTTP
[Backend API :3001]  ←─────────────┘
```

**Ports**
- Frontend: `3000` (Next.js)
- Backend: `3001` (Express + Execution Engine)
- Agents: `8000` (FastAPI + LLM mapping)

---

## 1) Frontend Layer (Visual Orchestrator)
**Role**: Visual workflow builder + demo interface.

**Core stack**
- Next.js 14, React 18, Tailwind CSS
- React Flow for DAG rendering

**Key modules**
- `frontend/components/flow-canvas.tsx` and `frontend/components/enhanced-flow-canvas.tsx` for DAG rendering
- `frontend/components/ai-chatbot-panel.tsx` for natural language input
- `frontend/lib/plugin-system/` for node templates and connection validation
- `frontend/components/node-config-panel.tsx` for node configuration UI

**Frontend runtime dependencies**
- Agent API: `NEXT_PUBLIC_AGENT_URL`
- Backend API: `NEXT_PUBLIC_BACKEND_URL`

**Frontend env file**
- `frontend/env.local.example`

---

## 2) Backend Layer (DeFi Execution Engine)
**Role**: Executes workflow DAGs with node executors.

**Core stack**
- Node.js + TypeScript
- Express API server
- Winston logging

**Execution engine**
- File: `backend/src/engine/execution-engine.ts`
- Builds execution plan, validates dependencies, runs nodes in parallel

**Node executors (selected)**
- `oneInchQuote`, `oneInchSwap` (1inch routing)
- `fusionSwap`, `fusionPlus`, `fusionMonadBridge`
- `priceImpactCalculator`, `transactionMonitor`, `transactionStatus`
- `walletConnector`, `tokenSelector`, `chainSelector`, `portfolioAPI`, `defiDashboard`

**Backend env file**
- `backend/env.example`

**Backend Docker image**
- Dockerfile: `backend/Dockerfile`
- Health check: `GET /api/health`

---

## 3) Agent Layer (Intelligence & Mapping)
**Role**: Converts natural language → structured workflow requirements → DAG.

**Core stack**
- Python 3.12, FastAPI
- Agno-AGI agent framework

**Key files**
- `agents/src/agents/architecture_mapper.py` (intent + pattern detection)
- `agents/src/workflow/generator.py` (workflow DAG construction)
- `agents/src/main.py` (API endpoints)

**Agent API endpoints**
- `POST /process` (NL input → workflow)
- `POST /approve-workflow` (execute workflow on backend)
- `GET /executions/{execution_id}` (status polling)

**LLM config**
- `AI_PROVIDER`, `AI_MODEL` read at runtime in `agents/src/main.py`
- Default: `openai`, `gpt-4o-mini`

---

## 🔁 End-to-End Request Flow (Golden Path)
1. **User input** in `ai-chatbot-panel.tsx`
2. **Agents API** parses intent → requirements
3. **WorkflowGenerator** builds DAG + config
4. **Frontend** renders React Flow canvas
5. **Approval** triggers backend execution
6. **Backend** executes node graph + emits status

---

## 🔌 API Integration Matrix

**Frontend → Agents**
- `POST /process`
- `POST /approve-workflow`

**Agents → Backend**
- `GET /api/health`
- `POST /api/workflows/execute`
- `GET /api/executions/{execution_id}`

**Backend (internal)**
- Node executors perform protocol-specific calls (1inch, Fusion, RPCs)

---

## 🔒 Security & Secrets Management
**Required env values** (minimum for demo):
- `ONEINCH_API_KEY`
- `ETHEREUM_RPC_URL`
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`

**Security behavior**
- Secrets are passed through execution context, not returned to UI
- Template mode lets nodes validate configs without performing real swaps

---

## ⚙️ Configuration Files

**Frontend**
- `frontend/env.local.example`
  - `NEXT_PUBLIC_BACKEND_URL`
  - `NEXT_PUBLIC_AGENT_URL`
  - `NEXT_PUBLIC_ONEINCH_API_KEY`
  - `NEXT_PUBLIC_SUPPORTED_CHAINS`

**Backend**
- `backend/env.example`
  - RPC URLs for chains
  - `ONEINCH_API_KEY`
  - `PORT`, `LOG_LEVEL`, `NODE_ENV`
  - `MAX_CONCURRENT_WORKFLOWS`, `NODE_TIMEOUT_MS`

---

## 📈 Scaling & Reliability Notes
- **Agent layer**: stateless and horizontally scalable
- **Backend layer**: bounded by `MAX_CONCURRENT_WORKFLOWS` and RPC rate limits
- **Frontend layer**: static and CDN-friendly
- **Fallback reliability**: regex fallback in `ArchitectureMapperAgent` ensures demo continuity

---

## 🧪 Demo/Validation Utilities
- `scripts/test-all-nodes.ts`
- `scripts/test-executable-nodes.ts`
- `scripts/test-swap-flow.ts`
- `scripts/demo-template-showcase.ts`

---

## 🧭 Architecture Document Alignment (Required Diagrams)
Use the sections below as **direct text for the Architecture Document template**.

### A) Use Case Diagram (Description)
**Primary actors**
- Researcher / Student (primary user)
- AI Agent Service
- DeFi Execution Engine
- Blockchain RPC Providers

**Core use cases**
- Submit natural language request
- Generate workflow graph
- Configure workflow nodes
- Approve workflow execution
- Monitor transaction status

**Mapping to modules**
- Submit request → `frontend/components/ai-chatbot-panel.tsx`
- Generate workflow → `agents/src/agents/architecture_mapper.py`
- Build DAG → `agents/src/workflow/generator.py`
- Execute DAG → `backend/src/engine/execution-engine.ts`

---

### B) Data Flow Diagram (DFD) (Description)
**External entities**
- User
- Blockchain RPCs / 1inch / Fusion

**Processes**
1. Intent Capture (Frontend)
2. Intent Analysis (Agent)
3. Workflow Construction (Agent)
4. Execution Orchestration (Backend)
5. Result Monitoring (Backend → Frontend)

**Data stores**
- In-memory conversation context: `agents/src/main.py` (`state.conversations`)
- Execution state map: `backend/src/engine/execution-engine.ts` (`executions` map)

---

### C) Component Diagram (Description)
**Components**
- Frontend (Next.js + React Flow)
- Agent Service (FastAPI)
- Execution Engine (Express + Node Executors)
- External DeFi APIs (1inch, Fusion)
- RPC Providers

**Connections**
- Frontend → Agent Service (`/process`)
- Agent Service → Backend (`/api/workflows/execute`)
- Backend → DeFi APIs/RPCs (node executors)

---

### D) Sequence Diagram (Description)
**Scenario: User builds DEX Aggregator**
1. User enters request in UI
2. Frontend sends `POST /process` to Agents
3. Agent returns requirements + workflow
4. Frontend renders DAG
5. User approves → Frontend sends `POST /approve-workflow`
6. Agent calls backend `POST /api/workflows/execute`
7. Backend runs nodes and emits status
8. Frontend polls execution status

---

### E) Class Diagram (Description)
**Key classes/structures**
- `ArchitectureMapperAgent` (agents)
- `WorkflowGenerator` (agents)
- `DeFiExecutionEngine` (backend)
- `NodeExecutor` (backend interface)
- `WorkflowDefinition`, `FlowNode`, `FlowEdge` (backend types)

**Relationships**
- `WorkflowGenerator` creates `WorkflowDefinition`
- `DeFiExecutionEngine` executes `WorkflowDefinition`
- `DeFiExecutionEngine` owns multiple `NodeExecutor` implementations

---

### F) Deployment Diagram (Description)
**Runtime nodes**
- Client Browser (Next.js app)
- Agent Service (FastAPI container or VM)
- Backend Service (Node.js container)
- External services (1inch API, Fusion, RPC endpoints)

**Deployment notes**
- Backend container uses `backend/Dockerfile`
- Ports: 3000 (frontend), 3001 (backend), 8000 (agent)
- Secrets injected via `.env` files

---

*Prepared for Koan Team Gallants | School of Computing, SRMIST*
