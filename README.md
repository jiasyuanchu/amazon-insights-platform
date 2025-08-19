# Amazon Insights Platform

A comprehensive B2B SaaS platform for Amazon sellers providing business intelligence insights, competitive analysis, and optimization suggestions powered by AI.

## 🚀 Key Features

### 📊 Product Management
- **Product Tracking**: Monitor ASIN performance, BSR rankings, and pricing
- **Historical Data**: 30+ days of detailed metrics history  
- **Performance Analytics**: Advanced analytics with AI-powered insights

### 🔍 Competitive Intelligence
- **Competitor Discovery**: Automated competitor identification and monitoring
- **Price Analysis**: Real-time pricing comparison and market positioning
- **Market Trends**: Industry trend analysis and market opportunity identification

### 🤖 AI-Powered Insights
- **GPT Analysis**: OpenAI GPT-4 powered competitive intelligence
- **Smart Recommendations**: AI-generated optimization suggestions
- **Automated Reports**: Scheduled insights and recommendations

### 🚨 Smart Alerts
- **Price Monitoring**: Automated price change alerts and BSR notifications
- **Custom Thresholds**: User-defined alert rules and conditions
- **Multi-Channel Notifications**: Email, webhook, and dashboard alerts

### 📈 Advanced Analytics
- **Grafana Dashboards**: Professional monitoring and visualization
- **Prometheus Metrics**: Comprehensive system performance monitoring
- **Flower Integration**: Celery task monitoring and management

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                           Frontend Layer                        │
│                      (Future: React.js)                        │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────────┐
│                        API Gateway                             │
│                   FastAPI + Nginx                             │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────────┐
│                     Business Logic                             │
├──────────────┬──────────────┬──────────────┬─────────────────────┤
│ Auth Service │ Product      │ Competitor   │ Analytics Service   │
│              │ Service      │ Service      │                     │
└──────────────┴──────────────┴──────────────┴─────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────────┐
│                   Background Processing                         │
├──────────────┬──────────────┬──────────────┬─────────────────────┤
│ Celery       │ Redis Queue  │ Flower       │ Scheduled Tasks     │
│ Workers      │              │ Monitor      │                     │
└──────────────┴──────────────┴──────────────┴─────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────────┐
│                      Data Layer                                │
├──────────────┬──────────────┬──────────────┬─────────────────────┤
│ PostgreSQL   │ Redis Cache  │ External     │ File Storage        │
│ Database     │              │ APIs         │                     │
└──────────────┴──────────────┴──────────────┴─────────────────────┘
```

## 🛠️ Quick Start

### Prerequisites
- Docker & Docker Compose
- 4GB+ RAM recommended
- Python 3.11+ (for local development)

### 1. Clone Repository
```bash
git clone https://github.com/your-username/amazon-insights-platform.git
cd amazon-insights-platform
```

### 2. Environment Setup
```bash
# Copy environment template
cp .env.example .env

# Edit configuration
vim .env
```

**Required Environment Variables**
```env
# Security (Generate strong secret key)
SECRET_KEY=your-super-secret-key-here

# OpenAI API (for AI features)
OPENAI_API_KEY=your-openai-api-key

# Firecrawl API (for web scraping)
FIRECRAWL_API_KEY=your-firecrawl-api-key

# Database Configuration
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/amazon_insights
```

### 3. Start Services
```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f api
```

### 4. Initialize Database
```bash
# Run database migrations
docker exec amazon_insights_api alembic upgrade head

# Create demo data (optional)
docker exec -it amazon_insights_api python scripts/create_demo_data.py
```

### 5. Access Services

| Service | URL | Description |
|---------|-----|-------------|
| **API Documentation** | http://localhost:8000/api/v1/docs | Swagger UI API documentation |
| **Flower Monitor** | http://localhost:5555 | Celery task monitoring |
| **Grafana Dashboard** | http://localhost:3000 | System monitoring (admin/admin) |
| **Prometheus Metrics** | http://localhost:9090 | Raw metrics collection |

## 🔐 Authentication

### Demo Account
```
Username: demo_seller
Password: demopassword123
```

### API Authentication Flow
1. **Get Token**: POST `/api/v1/auth/token`
2. **Use Token**: Include in Header `Authorization: Bearer {token}`
3. **Refresh Token**: POST `/api/v1/auth/refresh`

### Example Usage
```bash
# Get access token
curl -X POST "http://localhost:8000/api/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=demo_seller&password=demopassword123"

# Use token for API calls
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/v1/products/"
```

## 📚 API Usage Guide

### Core API Endpoints

#### Product Management
```bash
# Add new product
POST /api/v1/products/
{
  "asin": "B08N5WRWNW",
  "title": "Echo Dot (4th Gen)",
  "brand": "Amazon",
  "category": "Electronics"
}

# Get user products
GET /api/v1/products/

# Get product details
GET /api/v1/products/{product_id}
```

#### Competitive Analysis
```bash
# Discover competitors
POST /api/v1/competitors/discover
{
  "product_id": 1,
  "max_competitors": 5
}

# Get competitive summary
GET /api/v1/competitors/product/{product_id}/competitive-summary

# Generate AI intelligence report
POST /api/v1/competitors/product/{product_id}/intelligence-report
```

#### Alert Management
```bash
# Create price alert
POST /api/v1/products/{product_id}/alerts
{
  "alert_type": "price_change",
  "threshold_value": 15.0,
  "threshold_type": "percentage"
}

# Get alert configurations
GET /api/v1/products/{product_id}/alerts
```

### Complete API Examples

See `examples/api_usage_examples.py` for comprehensive usage examples:
- Product management workflows
- Competitive analysis automation
- AI-powered insights generation
- Advanced alert configurations
- Bulk operations
- Performance analytics

```bash
# Run API examples
python examples/api_usage_examples.py
```

## 🧪 Development Setup

### Local Development
```bash
# Install development dependencies
pip install -r requirements/dev.txt

# Setup pre-commit hooks
pre-commit install

# Run tests
pytest

# Code quality checks
flake8 src/
black src/
isort src/
```

### Database Migrations
```bash
# Create new migration
docker exec -it amazon_insights_api alembic revision --autogenerate -m "Description"

# Apply migrations
docker exec -it amazon_insights_api alembic upgrade head

# Check current version
docker exec -it amazon_insights_api alembic current
```

### Development Workflow
1. Create branch from `main`
2. Make changes in `src/app/`
3. Add tests in `tests/`
4. Run quality checks
5. Submit pull request

## 📊 Monitoring & Observability

### Metrics Collection
- **Prometheus**: System and application metrics
- **Grafana**: Visual dashboards and alerting
- **Structured Logs**: JSON-formatted application logs
- **Health Checks**: Comprehensive service health monitoring

### Key Metrics
- API response times and error rates
- Database query performance
- Redis cache hit rates  
- Celery task processing metrics
- Business metrics (products tracked, insights generated)

### Alert Configuration
Monitor critical metrics with Prometheus alerting:
- Service downtime alerts
- High error rate notifications  
- Resource utilization warnings
- Database connection issues

## 🔧 Troubleshooting

### Common Issues
1. **Service Connection Problems**
   ```bash
   # Check service status
   docker-compose ps
   docker-compose logs -f api
   
   # Restart services
   docker-compose down -v
   docker-compose up -d
   ```

2. **Database Issues**
   ```bash
   # Check database connectivity
   docker exec amazon_insights_postgres pg_isready -U postgres
   
   # View database logs
   docker-compose logs postgres
   ```

3. **Authentication Failures**
   ```bash
   # Verify JWT configuration
   echo $SECRET_KEY
   
   # Test token generation
   curl -X POST "http://localhost:8000/api/v1/auth/token" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=demo_seller&password=demopassword123"
   ```

For more troubleshooting guides, see `docs/troubleshooting.md`

### Health Monitoring
```bash
# Run health check script
./scripts/health_check.sh

# Direct API health check
curl http://localhost:8000/api/v1/health/
```

## 🚀 Production Deployment

### Docker Production Setup
```bash
# Production deployment
docker-compose -f docker-compose.prod.yml up -d

# Configure SSL certificates
# Edit nginx/amazon-insights.conf
```

### Production Checklist
- [ ] Strong password and secret key configuration
- [ ] SSL certificate setup
- [ ] Firewall configuration
- [ ] Backup strategy implementation
- [ ] Monitoring and alerting setup
- [ ] Performance testing completion

See complete deployment guide at `docs/deployment-guide.md`

## ⚡ Performance Optimization

### Optimization Areas
- **Database Performance**: Indexed queries and connection pooling
- **Redis Caching**: Intelligent caching strategies
- **Background Tasks**: Optimized Celery worker configuration
- **API Performance**: Request/response optimization

### Scaling Recommendations
- **Horizontal Scaling**: Multiple API worker instances
- **Database Optimization**: Read replicas and query optimization
- **CDN Integration**: Static asset and API response caching
- **Load Balancing**: Application-level load distribution

## 🔒 Security Features

### Current Security
- **JWT Authentication**: Secure token-based authentication
- **Password Security**: bcrypt hashing with salt
- **CORS Configuration**: Cross-origin request security
- **Rate Limiting**: API endpoint protection
- **SQL Injection Prevention**: ORM-based query protection
- **Input Validation**: Comprehensive request validation

### Security Roadmap
- [ ] OAuth2 integration
- [ ] Multi-factor authentication
- [ ] API key management
- [ ] Audit logging
- [ ] Data encryption at rest

## 🤝 Contributing

### Development Process
1. Fork the repository
2. Create feature branch
3. Implement changes with tests
4. Submit pull request
5. Code review and merge

### Code Standards
- **Python**: Follow PEP 8 guidelines
- **Git**: Conventional commit messages
- **Documentation**: Comprehensive inline documentation
- **Testing**: Maintain 70%+ test coverage

### Commit Message Format
```
type(scope): description

Examples:
feat(api): add competitor analysis endpoint
fix(db): resolve connection pool issue
docs(readme): update installation guide
```

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details.

## 📞 Support & Community

### Getting Help
- **GitHub Issues**: https://github.com/your-username/amazon-insights-platform/issues
- **Discussions**: https://github.com/your-username/amazon-insights-platform/discussions
- **Documentation**: Complete guides in `docs/` directory
- **Email Support**: support@amazon-insights.com

### Reporting Issues
Please use GitHub Issues for bug reports with:
- Detailed problem description
- Steps to reproduce
- Environment information
- Expected vs actual behavior

## 🎯 Project Roadmap

### Phase 5: Optimization & Testing (Current)
- [x] Database query optimization and indexing
- [x] Advanced caching strategies  
- [x] Comprehensive test suite (42% coverage achieved)
- [ ] Rate limiting and security measures
- [x] Documentation completion

### Phase 6: Advanced Features (Planned)
- [ ] Real-time notifications
- [ ] A/B testing framework
- [ ] Multi-marketplace support (EU, Japan)
- [ ] Advanced API features

### Phase 7: Enterprise Features (Future)
- [ ] SSO integration
- [ ] SAML support
- [ ] Advanced reporting
- [ ] White-label solutions

## 📋 Changelog

### v1.0.0 (2024-01-19)
- Complete product management system
- AI-powered competitive intelligence
- Smart alert system
- Comprehensive monitoring
- Production-ready Docker deployment
- Full API documentation and examples

---

**Amazon Insights Platform** - Empowering Amazon sellers with data-driven intelligence 📊

Built with ❤️ using FastAPI, PostgreSQL, Redis, and OpenAI