# ML-Auditor Architecture (Mermaid)

```mermaid
flowchart LR
    %% ======================= Users =======================
    subgraph UI["🧑‍💻 Users"]
        B["Browser"]
    end

    %% ======================= Frontend =======================
    subgraph FE["Frontend · Next.js / React"]
        F["Next.js App<br/>:3000"]
        WS["WebSocket client<br/>/ws/alerts /analytics /notifications"]
    end

    %% ======================= Backend =======================
    subgraph BE["Backend · Django 4.2 / Ninja / LangGraph"]
        API["REST API :8000<br/>Django Ninja"]
        AG["Agent Orchestration<br/>agent_command → agent_graph<br/>(LangGraph: RAG→LLM→Tools loop)"]
        TOOL["ToolExecutor<br/>task / note / email / calendar<br/>jira / kijiji / plaid / canva / bank-pdf"]
        CEL["Celery Worker + Beat<br/>sync_jira · sync_plaid · sync_gmail<br/>scrape_news · analyze_email"]
        CH["Channels consumers<br/>alerts / analytics / notifications"]
        MCP["MCP Server :8100<br/>StreamableHTTP (FastMCP)"]
    end

    %% ======================= Storage =======================
    subgraph STORE["Storage"]
        PG[("PostgreSQL 16 + pgvector<br/>:5432")]
        RD[("Redis 7 :6379<br/>cache · Celery broker · Channels")]
        MEDIA[("Media / static<br/>PDFs · uploads")]
    end

    %% ======================= AI / ML =======================
    subgraph AI["AI / ML Layer"]
        WT["Web Tools :8090<br/>Agent-Reach (web read/search/RSS)"]
        JC["JobChameleon :8787/:8788<br/>AI job-intelligence gateway + MCP"]
        JCA["JobCamelonapp :8088/:8790/:1403<br/>full workbench (on-demand container)"]
        NIM["NVIDIA NIM (cloud)<br/>chat · embeddings"]
    end

    %% ======================= ELK =======================
    subgraph ELK["Logging · ELK 8.13"]
        ES[("Elasticsearch :9200<br/>ml-auditor-* indices")]
        LS["Logstash :5000/:5044<br/>filebeat beats input + TCP"]
        KI["Kibana :5601<br/>dashboards"]
        FB["Filebeat<br/>ships logs/*.log"]
        MB["Metricbeat<br/>system + container metrics"]
    end

    %% ======================= External =======================
    subgraph EXT["External Integrations"]
        PLAID["Plaid (banking)"]
        GMAIL["Gmail / Google Calendar"]
        CANVA["Canva"]
        JIRA["Jira"]
        KIJIJI["Kijiji"]
        EXA["EXA (web search)"]
        JCAPI["JobChameleon API"]
    end

    %% ======================= Flows =======================
    B -->|"HTTP :3000"| F
    B -->|"WS"| WS
    F -->|"REST /api · JWT Bearer<br/>NEXT_PUBLIC_API_URL"| API
    WS -->|"Channels WS :8000"| CH

    API --> AG
    API --> CEL
    API --> CH
    API --> MCP

    AG --> TOOL
    AG -->|"ChatOpenAI · bind_tools"| NIM
    AG -->|"embeddings"| NIM
    AG -->|"RAG context"| PG
    TOOL -->|"ORM / queries"| PG
    CEL -->|"ORM"| PG
    CEL -->|"broker / result"| RD
    CH -->|"channel layer"| RD
    MCP -->|"DB access"| PG
    MCP --> WT

    TOOL --> PLAID
    TOOL --> GMAIL
    TOOL --> CANVA
    TOOL --> JIRA
    TOOL --> KIJIJI
    AG -->|"unused client (removed)"| JC
    WT -->|"EXA_API_KEY"| EXA
    JC --> JCAPI
    JC -->|"NIM key/model"| NIM
    JCA -->|"JC_MCP_URL :8788/mcp"| JC
    MCP --> JC

    %% ELK ingestion
    API -->|"JSON logs"| FB
    CEL -->|"JSON logs"| FB
    F -->|"POST /api/logs/"| API
    FB -->|"beats :5044"| LS
    API -->|"TCP :5000 (optional)"| LS
    LS -->|"ml-auditor-* indices"| ES
    MB --> ES
    ES --> KI
