# Alternative Investments Document Intelligence Platform

A modern, AI-native platform for financial institutions to automate ingestion, classification, extraction, normalization, storage, and presentation of unstructured alternative-investment documents.

## Diagram
### You can find the diagram [HERE](https://www.mermaidchart.com/app/projects/d9aec1d5-20e4-425a-8161-d213e95e0bd4/diagrams/e83ca801-9df4-4752-ab2f-2bbda63013a2/version/v0.1/edit).
## Features

- **Document Processing Pipeline**: Automated PDF ingestion and text extraction
- **AI Classification**: Machine learning-based document type detection
- **Field Extraction**: Intelligent extraction of key financial data points
- **RESTful API**: Comprehensive API for integration
- **Web Interface**: Simple UI for testing and document management
- **Real-time Processing**: Asynchronous document processing with status updates
- **Database Storage**: Structured storage with PostgreSQL
- **Observability**: Comprehensive logging and monitoring

## Architecture

### High-Level Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Ingestion     │    │  Classification │    │   Extraction    │
│   Service       │───▶│    Service      │───▶│    Service      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  PostgreSQL     │    │   File Store    │    │   Processing    │
│   Database      │    │                 │    │     Logs        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Supported Document Types

1. **Capital Call Notices** - Extracts fund ID, call date, LP ID, call amount, currency, call number
2. **Distribution Notices** - Extracts fund ID, distribution date, LP ID, amount, type (ROC/CI)
3. **Valuation Reports** - Extracts valuation date, methodology, inputs, final valuation
4. **Quarterly Updates** - Extracts KPIs and narrative highlights

## Quick Start

### Using Docker (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd document-intelligence
   ```

2. **Start services**
   ```bash
   docker-compose up -d
   ```

3. **Access the application**
   - Web UI: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Database Admin: http://localhost:8080 (adminer)

### Manual Setup

1. **Prerequisites**
   - Python 3.11+
   - PostgreSQL 13+
   - Redis (optional, for caching)

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   ```

3. **Set up database**
   ```bash
   createdb doc_intelligence
   # Update DATABASE_URL in .env
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Run the application**
   ```bash
   uvicorn main:app --reload
   ```

## API Documentation

### Document Upload
```bash
curl -X POST "http://localhost:8000/api/v1/documents" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"
```

### List Documents
```bash
curl "http://localhost:8000/api/v1/documents?document_type=capital_call&status=completed"
```

### Get Capital Calls
```bash
curl "http://localhost:8000/api/v1/capital-calls?fund_id=ABC-III&start_date=2023-01-01"
```

### Get Dashboard Analytics
```bash
curl "http://localhost:8000/api/v1/analytics/dashboard"
```

## Testing

### Run Unit Tests
```bash
pytest tests/ -v
```

### Run Integration Tests
```bash
pytest tests/integration/ -v
```

### Performance Testing
```bash
pytest tests/performance/ -v
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://...` |
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8000` |
| `DEBUG` | Enable debug mode | `true` |
| `MAX_FILE_SIZE` | Maximum file size (bytes) | `52428800` |
| `MODEL_CACHE_DIR` | ML models cache directory | `models` |

## Deployment

### Production Deployment with Kubernetes

1. **Build and push Docker image**
   ```bash
   docker build -t your-registry/doc-intelligence:latest .
   docker push your-registry/doc-intelligence:latest
   ```

2. **Deploy to Kubernetes**
   ```bash
   kubectl apply -f k8s/
   ```

### CI/CD Pipeline

The project includes GitHub Actions workflow for:
- Automated testing
- Security scanning
- Docker image building
- Deployment to staging/production

## Monitoring & Observability

### Health Checks
- Application health: `GET /health`
- Database connectivity check
- Processing pipeline status

### Logging
- Structured logging with correlation IDs
- Processing step tracking
- Error tracking and alerting

### Metrics
- Document processing throughput
- Classification accuracy
- API response times
- System resource usage

## Security

### Authentication & Authorization
- JWT token-based authentication
- Role-based access control (RBAC)
- API rate limiting

### Data Protection
- TLS 1.3 encryption in transit
- AES-256 encryption at rest
- Secure file upload validation
- SQL injection prevention

## Performance Optimization

### Scaling Strategy
- Horizontal scaling for API services
- Async processing for document pipeline
- Database connection pooling
- Redis caching for frequently accessed data

### Performance Targets
- Document processing: < 30 seconds per document
- API response time: < 200ms (95th percentile)
- Concurrent processing: 100+ documents
- Uptime: 99.9% SLA

## Best Practices Implemented

### Code Quality
- Type hints throughout codebase
- Comprehensive error handling
- Async/await for I/O operations
- Clean architecture with separation of concerns

### Database Design
- Proper indexing for query performance
- Foreign key constraints for data integrity
- Audit logging for compliance
- Connection pooling for efficiency

### ML/AI Best Practices
- Model versioning and fallback strategies
- Confidence scoring for all predictions
- A/B testing framework ready
- Data quality validation

## Lessons from Past Attempts

### Common Pitfalls Avoided
1. **Poor Model Fallback** - Implemented multi-tier classification with rule-based fallbacks
2. **Brittle Pipelines** - Robust error handling and retry mechanisms
3. **Lack of Observability** - Comprehensive logging and monitoring throughout
4. **Poor Scalability** - Async processing and horizontal scaling design
5. **Data Quality Issues** - Validation and confidence scoring at every step

## Future Enhancements

### Vision: Beyond Document Processing

**Recommended Next Domain: ESG Reporting Automation**

Why ESG Reporting:
1. **Market Demand** - Growing regulatory requirements (EU SFDR, SEC climate rules)
2. **Data Complexity** - Unstructured ESG data from multiple sources
3. **High Value** - Significant cost savings from automation
4. **Competitive Advantage** - Early market entry opportunity

**Implementation Approach**:
- Extend current pipeline for ESG document types
- Add sustainability metrics extraction
- Implement regulatory reporting templates
- Build ESG scoring algorithms

### Technical Roadmap
1. **Multi-language Support** - Process documents in multiple languages
2. **Advanced ML Models** - Fine-tuned transformers for financial documents  
3. **Real-time Collaboration** - Multi-user annotation and correction system
4. **Integration Ecosystem** - Connectors for major financial systems
5. **Mobile Applications** - On-the-go document processing

