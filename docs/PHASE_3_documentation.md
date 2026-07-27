# Phase 3: ML Python & Clustering

## Overview
Implementation of the ML microservice with CrewAI agents and NVIDIA NIM integration.

## Architecture

```
ml-service/
├── main.py                     # FastAPI application
├── requirements.txt            # Python dependencies
├── .env.example                # Configuration template
├── app/
│   ├── api/
│   │   └── routes.py           # API endpoints
│   └── services/
│       ├── database.py         # SQLAlchemy async
│       ├── nim_service.py      # NVIDIA NIM client
│       ├── crewai_agents.py    # CrewAI agents
│       ├── email_analysis.py   # Email classification
│       ├── financial_analysis.py # Isolation Forest
│       ├── embedding_service.py # Embedding generation
│       └── search_service.py   # RAG & document search
└── tests/
```

## Services Implemented

### 1. NIMService (NVIDIA NIM)
- Chat completion with Llama 3.3 / DeepSeek V3
- Text classification
- Entity extraction
- Embedding generation (384 dimensions)

### 2. CrewAI Agents
- **EmailClusteringAgent**: Classifies emails into 5 categories (promotional, transactional, social, spam, important)
- **FinancialAuditAgent**: Detects anomalies in financial transactions
- **KijijiNegotiationAgent**: Analyzes marketplace messages for spam/negotiation

### 3. EmailAnalysisService
- Email classification with confidence scores
- Entity extraction (amounts, dates, names, organizations)
- Priority scoring
- Batch processing support

### 4. FinancialAnalysisService
- Isolation Forest anomaly detection
- Pearson correlation analysis
- Subscription detection
- Category statistics

### 5. EmbeddingService
- Text embedding generation (384D)
- Batch embedding support
- Text chunking with overlap
- Cosine similarity computation

### 6. SearchService
- Semantic document search
- RAG context generation
- Entity extraction from text

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/analyze-email` | POST | Classify email + extract entities |
| `/api/v1/analyze-emails-batch` | POST | Batch email analysis |
| `/api/v1/chunk-email` | POST | Chunk email for processing |
| `/api/v1/detect-anomalies` | POST | Isolation Forest detection |
| `/api/v1/financial-insights` | POST | Correlations & subscriptions |
| `/api/v1/generate-embeddings` | POST | Generate embeddings |
| `/api/v1/chunk-and-embed` | POST | Chunk text + embed |
| `/api/v1/search-documents` | POST | Semantic search |
| `/api/v1/rag-context` | POST | Get RAG context |
| `/api/v1/analyze-kijiji-message` | POST | Analyze Kijiji message |
| `/api/v1/batch-embedding-job` | POST | Queue batch embeddings |

## Configuration

```bash
# Environment variables
DATABASE_URL=postgresql+asyncpg://mlauditor:mlauditor@localhost:5432/mlauditor_db
NIM_API_KEY=your_nvidia_nim_key
NIM_BASE_URL=https://integrate.api.nvidia.com/v1
NIM_MODEL=meta/llama-3.3-70b-instruct
NIM_EMBEDDING_MODEL=nvidia/nv-embedqa-e5-v5
```

## Testing

```bash
# Install dependencies
cd ml-service
pip install -r requirements.txt

# Run service
uvicorn main:app --reload --port 8001

# Access docs
open http://localhost:8001/docs
```

## Docker

The ML service is included in docker-compose.yml:

```bash
docker-compose up ml_service
```

## Dependencies

- FastAPI 0.115.0
- CrewAI 0.86.0
- NVIDIA NIM SDK 0.7.0
- scikit-learn 1.5.0
- sentence-transformers 3.3.0
- numpy, pandas, scipy
- structlog (logging)
