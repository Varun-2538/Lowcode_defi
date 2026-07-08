# 📋 Project Backlog (MS Planner Blueprint)

This document maps our project objectives into **Epics**, **User Stories**, and **Acceptance Criteria** as required for the MS Planner board.

---

## 🏆 Epic 1: Intelligent Requirement Analysis (NLP)
**Objective**: Build a natural language interface to interpret DeFi requirements.

### **User Story 1.1: Intent Recognition**
- **As a** researcher
- **I want to** type my DeFi needs in plain English
- **So that** the system can distinguish between a greeting and a technical request.
- **Acceptance Criteria**:
    - [ ] Correctly identifies "swap", "bridge", and "limit order" intents.
    - [ ] Triggers `_fallback_analysis` when LLM is unavailable.
    - [ ] Returns "conversational" pattern for non-DeFi inputs.

### **User Story 1.2: Metadata Extraction**
- **As a** developer
- **I want** the agent to extract specific tokens and chains from the input
- **So that** nodes are configured automatically.
- **Acceptance Criteria**:
    - [ ] Extracts token symbols (ETH, USDC, WBTC).
    - [ ] Maps chain names to Chain IDs (e.g., Polygon -> 137).

---

## 🏗️ Epic 2: Automated Workflow Synthesis
**Objective**: Transform extracted requirements into a visual Directed Acyclic Graph (DAG).

### **User Story 2.1: Graph Orchestration**
- **As a** non-technical user
- **I want** the system to suggest a complete suite of nodes
- **So that** I don't miss security or monitoring modules.
- **Acceptance Criteria**:
    - [ ] Automatically injects `priceImpactCalculator` for swap intents.
    - [ ] Automatically injects `transactionMonitor` for all execution intents.

### **User Story 2.2: Spatial UI Management**
- **As a** user
- **I want** the generated canvas nodes to be organized
- **So that** I can easily read the data flow.
- **Acceptance Criteria**:
    - [ ] Nodes are placed on a non-overlapping grid.
    - [ ] Edges are correctly routed from source to target handles.

---

## ⚙️ Epic 3: Secure DeFi Execution Engine
**Objective**: Implement the backend logic to execute 1inch and Fusion protocols.

### **User Story 3.1: Sequential Node Execution**
- **As a** trader
- **I want** my workflow to execute in the correct order
- **So that** the swap doesn't happen before the wallet is connected.
- **Acceptance Criteria**:
    - [ ] Engine performs a topological sort before execution.
    - [ ] Execution stops and reports error if a mandatory dependency fails.

### **User Story 3.2: Multi-Chain Bridging**
- **As a** user
- **I want** to bridge assets between chains using intent-based systems
- **So that** I get MEV protection and lower fees.
- **Acceptance Criteria**:
    - [ ] `fusionPlus` node successfully initiates a cross-chain intent.
    - [ ] Status is tracked across the bridge lifecycle.

---

## 📊 Sprint 1 Status (January 2026)
| Task | Status | Assignee |
| :--- | :--- | :--- |
| Initialize ArchitectureMapperAgent | Completed | AI Agent |
| Implement 1inch Quote/Swap Executors | Completed | Backend Dev |
| Build React Flow Canvas | Completed | Frontend Dev |
| Create IEEE Research Draft | In Progress | Researcher |
| MS Planner Board Setup | In Progress | All |
