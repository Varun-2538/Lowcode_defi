# 🤖 AI Agents in Koan (Unite DeFi)

## 📌 Purpose of This File
This document expands the agentic architecture details and maps them directly to **First Review** requirements, the **Project Handbook**, and the **Validation Form**. It is written as a working guide the team can use to fill review deliverables quickly and consistently.

**Primary sources used**
- `INSTRUCTIONS TO STUDENTS FOR FIRST REVIEW_Research projects.docx`
- `Project Handbook.docx`
- `Major Project Validation Form.docx`
- `Project Documents/Architecture Document (3).docx`
- `Project Documents/Functional Document (3).docx`
- `Project Documents/Functional Test case Template (6).xlsx`
- `Project Documents/Sprint Retrospective (2) (1).xlsx`
- `Compiled Keywords of SDG Mapping for publications.xlsx`
- Codebase (`agents/`, `backend/`, `frontend/`)

---

## ✅ First Review Deliverables Checklist (Research Project)
**Must submit during Review 1 (06.01.2026):**
1. **Review PPT** (team presentation + demo)
2. **Project Handbook** (`Project Handbook.docx`)
3. **Major Project Validation Form** (`Major Project Validation Form.docx`)
4. **Initial Research Article (IEEE format)** or **Patent Draft**
5. **Daily Scrum Updates** (MS Planner + OneNote screenshots/exports)
6. **Architecture Document** (`Project Documents/Architecture Document (3).docx`)
7. **Functional Document** (`Project Documents/Functional Document (3).docx`)
8. **Functional Test Case + Result Analysis** (`Project Documents/Functional Test case Template (6).xlsx`)
9. **Sprint Retrospective** (`Project Documents/Sprint Retrospective (2) (1).xlsx`)

**Important review constraints from instructions:**
- Identify objectives and treat each objective as an **Epic**
- Maintain a **product backlog** in MS Planner with **user stories + acceptance criteria**
- Implement **1–2 epics** depending on complexity
- Weekly progress update to guide is mandatory
- Individual evaluation even if team project
- Publication/patent responsibility rests with students

---

## 🎯 Research Alignment & SDG Mapping (Based on Compiled Keywords)
The SDG keyword sheet contains ~750+ terms. Below are the **closest SDG clusters** for Koan, with **keyword evidence** pulled from the mapping list.

### ✅ Primary SDG Alignment
**SDG 9 – Industry, Innovation, and Infrastructure**
Evidence keywords from mapping file:
`Resilient infrastructure`, `Sustainable infrastructure`, `ICT infrastructure`, `Network infrastructure`, `Infrastructure`, `Industry, innovation and infrastructure`
Koan mapping:
- No-code **workflow infrastructure** for DeFi
- Execution engine and node registry provide extensible infrastructure
- Cross-chain and protocol abstraction fosters infrastructure innovation

**SDG 17 – Partnerships for the Goals**
Evidence keywords from mapping file:
`Global partnership for sustainable development`, `Public-private partnerships`, `Civil society partnerships`, `Global partnership`, `Multi-stakeholder partnerships`, `Partnerships for the goals`
Koan mapping:
- Multi-protocol orchestration across **1inch**, **Fusion**, **Uniswap**, **Aave**, **Chainlink**
- Modular nodes allow **protocol collaboration** and composable flows
- Cross-chain workflows encourage interoperable coordination

### ✅ Secondary SDG Alignment (Supportive)
**SDG 10 – Reduced Inequalities**
Evidence keywords:
`Inclusion`, `Social inclusion`, `Financial services`
Koan mapping:
- `walletConnector` + `tokenSelector` reduce access barriers
- Visual workflows enable non-technical user participation

**SDG 12 – Responsible Consumption and Production**
Evidence keywords:
`Recycling`, `Responsible production chains`, `Efficient use of resources`, `Energy efficiency`
Koan mapping:
- `priceImpactCalculator` and `transactionMonitor` help prevent wasteful execution
- Gas optimization settings in `oneInchQuote` and `oneInchSwap`

**SDG 16 – Peace, Justice, and Strong Institutions**
Evidence keywords:
`Transparency`, `Accountability`, `Rule of law`
Koan mapping:
- Auditable workflow logs, execution history, deterministic configuration

---

## 🏗️ Agentic Architecture (Code-Accurate)
Koan uses **two main AI components**: the **ArchitectureMapperAgent** (reasoning + intent) and the **WorkflowGenerator** (DAG assembly + config), coordinated through a FastAPI service and connected to the TypeScript execution backend.

### 1) ArchitectureMapperAgent (`agents/src/agents/architecture_mapper.py`)
Purpose: Convert natural language into structured DeFi workflow requirements.
Key behaviors:
- **Provider-agnostic LLM** (`openai` or `anthropic`) with strict JSON output
- **Conversational detection** to avoid accidental workflow creation
- **Fallback regex analysis** if LLM fails
- Extracts:
  - pattern (DEX Aggregator / Limit Order / Cross-Chain)
  - tokens, chains, features
  - suggested node types

Signal handling logic:
- If missing strong DeFi + action signals → treated as conversational
- Conversational inputs return no nodes (safe default)

### 2) WorkflowGenerator (`agents/src/workflow/generator.py`)
Purpose: Convert requirements into executable workflow definition.
Key behaviors:
- Assigns **workflow metadata** (version, author, pattern, tokens)
- Generates **nodes, edges, layout positions**
- Adds **template defaults** and **node config hydration**
- Special presets for known patterns:
  - DEX Aggregator (10-node suite)
  - Cross-Chain Bridge
  - Limit Order Application

Example DEX Aggregator auto-suite:
`walletConnector → tokenSelector → oneInchQuote → priceImpactCalculator → oneInchSwap → fusionSwap → limitOrder → portfolioAPI → transactionMonitor → defiDashboard`

### 3) Agent API Layer (`agents/src/main.py`)
FastAPI endpoints:
- `POST /process` – Analyze request, build workflow
- `POST /approve-workflow` – Execute workflow on backend
- `GET /executions/{execution_id}` – Poll execution status

Conversation context stored in-memory:
`state.conversations[conversation_id]` holds history + requirements + workflow.

### 4) Backend Client (`agents/src/api/backend_client.py`)
Functions:
- health check at `/api/health`
- workflow execution at `/api/workflows/execute`
- execution status + logs + cancel

---

## ⚙️ Execution Engine (Backend)
**DeFiExecutionEngine** (`backend/src/engine/execution-engine.ts`) builds and executes a DAG:
- Builds execution plan from nodes + edges
- Detects circular dependencies
- Executes independent nodes in parallel
- Emits `execution.started`, `execution.completed`, `execution.failed`
- Stores execution context and step results

This engine is the core runtime for any workflow generated by agents.

---

## 🧩 Node Executor Catalog (Backend)
These are the **actual executable node types** currently registered in the codebase:

**Core DeFi Nodes**
- `walletConnector`
- `tokenSelector`
- `oneInchQuote`
- `oneInchSwap`
- `priceImpactCalculator`
- `transactionMonitor`
- `transactionStatus`
- `limitOrder`
- `portfolioAPI`
- `defiDashboard`
- `fusionSwap`
- `fusionPlus`
- `fusionMonadBridge`
- `chainSelector`
- `erc20Token`

**Infrastructure/Utility Nodes**
- `l1Config`
- `l1SimulatorDeployer`
- `icmSender`
- `icmReceiver`

**Why this matters for Review:**
These node types are the actual backend capabilities; any architecture/functional/test documents should reference these as system modules.

---

## 🧠 Frontend Integration (React Flow + Plugin System)
Key frontend modules:
- `frontend/components/flow-canvas.tsx` + `frontend/components/enhanced-flow-canvas.tsx` for rendering workflows
- `frontend/lib/plugin-system/` for node templates + validation
- `frontend/components/node-config-panel.tsx` for config editing
- `frontend/components/ai-chatbot-panel.tsx` for natural language input

This directly supports the **“visual hydration”** stage in the demo.

---

## 📊 First Review Mapping to Required Documents

### 1) Major Project Validation Form (`Major Project Validation Form.docx`)
Use the following content in the form (fill values as required by faculty):

**Abstract (short)**
- Koan is a no-code DeFi workflow platform that converts natural-language intent into executable DAGs using AI agents.

**Research Gap (3 points)**
- DeFi tooling is fragmented across protocols and requires developer-only expertise.
- Existing no-code tools lack safe execution and multi-protocol orchestration.
- Limited research on AI agents that enforce workflow safety and structure in DeFi.

**5 Research Articles / Patent References**
- Fill with 5 IEEE-style citations that informed 1inch/Fusion/agent workflows.

**Bridging the Gap (3 points)**
- Conversational AI to workflow DAG conversion
- Built-in protocol templates and safety nodes (price impact, monitoring)
- Cross-chain abstractions with automatic orchestration

**Objectives (max 5)**
1. Convert NL intent into DeFi workflow graph (ArchitectureMapperAgent)
2. Auto-synthesize executable DAG (WorkflowGenerator + Execution Engine)
3. Enable cross-chain and multi-protocol orchestration (Fusion+, 1inch)
4. Provide live monitoring + transparency (transactionMonitor + dashboard)
5. Validate safe execution with template + config checks

**Methodology (max 10 points)**
- Intent parsing with LLM + fallback rules
- Pattern-based node selection
- Config hydration (template mode)
- DAG validation + dependency checks
- Execution engine with node executors
- UI canvas visualization and configuration
- Health check + runtime monitoring

**Outcomes / Deliverables (max 5)**
- AI agent service (FastAPI)
- Executable workflow engine (TypeScript)
- Frontend visual designer
- DeFi node library
- Demo workflows + test scripts

**Novelty (max 3)**
- Deterministic LLM-to-DAG conversion
- Hybrid LLM + regex fallback for reliability
- Multi-protocol orchestration with template safety defaults

**TRL suggestion**
- Suggested: **TRL 4–5** (validated in lab with working prototype). Adjust if needed.

**SDG**
- Primary: **SDG 9**, Secondary: **SDG 17**

---

### 2) Architecture Document (`Project Documents/Architecture Document (3).docx`)
Required diagrams: **use case, class, DFD, component, sequence, deployment**.

**Recommended architecture choice**:
- **Microservices** (Frontend, Backend, Agents)

**High-Level Architecture**
- User → Frontend (React Flow) → Agents API (FastAPI) → Backend Engine

**Low-Level Architecture**
- ArchitectureMapperAgent (LLM + fallback)
- WorkflowGenerator (DAG creation + configuration)
- DeFiExecutionEngine (DAG execution + logging)
- Node Executors (1inch, Fusion, Token Selector, etc.)

**Add “necessary legends” in diagrams:**
- Node types
- Execution state (pending/running/completed)
- Data flow (request → workflow → execution result)

---

### 3) Functional Document (`Project Documents/Functional Document (3).docx`)
Fill with Koan data:

- **Introduction**: No-code DeFi platform for workflow design and execution.
- **Product Goal**: Convert natural language into safe, executable DeFi workflows.
- **Demography**:
  - Users: Researchers, finance students, DeFi developers, non-technical users
  - Location: Global
- **Business Processes**:
  - User submits intent → AI analysis → workflow preview → approval → execution
- **Features (examples)**:
  - Natural language workflow generation
  - Cross-chain bridging
  - Portfolio dashboard
  - MEV-protected swap execution
- **Authorization Matrix** (example):
  - Admin: full access
  - User: create + execute workflows
  - Guest: read-only preview
- **Assumptions**:
  - API keys are available for 1inch/Fusion
  - Supported chains are reachable via RPC

---

### 4) Functional Test Case Template (`Project Documents/Functional Test case Template (6).xlsx`)
Template columns seen in file:
- `Feature`
- `Test Case`
- `Steps to execute test case`
- `Expected Output`
- `Actual Output`
- `Status`
- `More Information`

Suggested test cases (align with real nodes):
1. **Natural Language → Workflow**
   - Input: “Create a swap app for ETH/USDC”
   - Expected: DEX Aggregator pattern, nodes generated
2. **1inch Quote Node**
   - Input: ETH→USDC config
   - Expected: quote_result + route returned
3. **Price Impact Calculator**
   - Input: simulated high impact trade
   - Expected: warning threshold triggered
4. **Cross-chain Bridge**
   - Input: Ethereum → Polygon
   - Expected: fusionPlus configured with both chains
5. **Transaction Monitor**
   - Input: mock transaction hash
   - Expected: confirmation + status update

---

### 5) Sprint Retrospective (`Project Documents/Sprint Retrospective (2) (1).xlsx`)
Template sections in file:
- **What went well**
- **What went poorly**
  - Example in template: “Requirements changed mid-sprint.”
- **What ideas do you have**
- **How should we take action**

Populate with sprint-specific insights (tooling stability, API changes, LLM accuracy).

---

## 🧭 Epic → User Story Mapping (Agile Requirement)
Each **Objective = Epic**. Suggested epics for Koan:

**Epic 1: NLP Intent Parsing**
- User story: “As a non-technical researcher, I want to describe DeFi goals in natural language so I can prototype without coding.”
- Acceptance: Given NL input, system returns pattern + node list with ≥ 90% accuracy in test cases.

**Epic 2: Workflow Synthesis**
- User story: “As a developer, I want a full DAG auto-generated with safety nodes.”
- Acceptance: Workflow contains required nodes + valid edges + config defaults.

**Epic 3: Multi-Chain Interoperability**
- User story: “As a trader, I want cross-chain swaps with status monitoring.”
- Acceptance: fusionPlus + chainSelector + transactionMonitor present in workflow.

**Epic 4: Monitoring & Transparency**
- User story: “As a reviewer, I want to see execution status and analytics.”
- Acceptance: transactionMonitor + defiDashboard outputs visible.

---

## 🚀 First Review Demo Script (Recommended)
**Input:** “Build a secure swap app for WBTC and ETH with a live dashboard.”
1. **Intent Discovery** – ArchitectureMapperAgent extracts swap pattern + tokens
2. **Structural Inference** – Suggests `oneInchQuote`, `priceImpactCalculator`, `transactionMonitor`
3. **Workflow Generation** – 10-node DAG built in <2s
4. **Canvas Display** – React Flow renders DAG
5. **Validation** – health check + preview execution

---

## 🧪 Evidence Assets in Repo (Use in Review)
- Demo scripts: `scripts/demo-template-showcase.ts`, `scripts/test-all-nodes.ts`
- Execution engine tests: `scripts/test-executable-nodes.ts`, `scripts/test-swap-flow.ts`
- Frontend demos: `frontend/app/demo/*`
- Architecture image: `Architecture.png`

---

## 📝 Notes for Review Team
- **LLM fallback** guarantees demo reliability when OpenAI/Anthropic is unreachable.
- **Template creation mode** is supported by node executors to ensure safe, config-only preview before execution.
- **Workflow validation** is built into `WorkflowGenerator.validate_workflow`.

---

*Prepared for Koan Team Gallants | School of Computing, SRMIST*
