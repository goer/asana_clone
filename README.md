# Asana Clone - FastAPI Backend with MCP Integration

A full-featured Asana clone backend built with FastAPI, PostgreSQL, and Model Context Protocol (MCP) integration.

## Features

- ✅ **Complete REST API** - User authentication, workspaces, projects, tasks, teams, and more
- ✅ **MCP Integration** - Expose API endpoints as MCP tools for LLM interaction
- ✅ **API Key Authentication** - Secure MCP server with simple API key auth
- ✅ **PostgreSQL Database** - Robust relational data storage
- ✅ **Docker Compose** - Easy deployment and development
- ✅ **Full Test Suite** - Comprehensive API tests
- ✅ **JWT Authentication** - Secure user authentication for API endpoints

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd asana_clone
```

### 2. Configure Environment

Copy `.env.example` to `.env` and update values:

```bash
cp .env.example .env
```

Key environment variables:
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - JWT secret key
- `MCP_API_KEY` - API key for MCP server access

### 3. Start with Docker Compose

```bash
docker-compose up -d
```

This will start:
- PostgreSQL database on port 5432
- FastAPI server on port 8000

### 4. Run Database Migrations

```bash
docker-compose exec api alembic upgrade head
```

## API Endpoints

### Authentication
- `POST /api/register` - Register a new user
- `POST /api/login` - Login and get JWT token

### Workspaces
- `POST /api/workspaces` - Create workspace
- `GET /api/workspaces` - List user's workspaces
- `GET /api/workspaces/{id}` - Get workspace details

### Projects
- `POST /api/projects` - Create project
- `GET /api/projects/{workspace_id}` - List workspace projects

### Tasks
- `POST /api/tasks` - Create task
- `GET /api/tasks/{project_id}` - List project tasks
- `PATCH /api/tasks/{id}` - Update task

### Teams
- `POST /api/teams` - Create team
- `POST /api/teams/{id}/members` - Add team member

## MCP Integration

This project includes a Model Context Protocol (MCP) server that exposes API endpoints as tools for LLM interaction.

### MCP Endpoints

The MCP server is available at `http://localhost:8000/mcp-api/mcp`

**Authentication Required:** All MCP requests require the `X-API-Key` header.

### Simplified MCP API

- `POST /mcp-api/mcp/auth/register` - Register user via MCP
- `POST /mcp-api/mcp/auth/login` - Login via MCP
- `POST /mcp-api/mcp/workspaces` - Create workspace via MCP
- `GET /mcp-api/mcp/health` - Health check

### Using MCP with API Key

All MCP requests require authentication:

```bash
curl -X POST http://localhost:8000/mcp-api/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "X-API-Key: asana-mcp-secret-key-2025" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize",...}'
```

For complete MCP authentication documentation, see **[MCP_AUTH_GUIDE.md](MCP_AUTH_GUIDE.md)**

## Testing

Run the test suite:

```bash
# Run all tests
docker-compose exec api pytest

# Run specific test file
docker-compose exec api pytest tests/test_api.py

# Run with verbose output
docker-compose exec api pytest -vv
```

## Development

### Project Structure

```
asana_clone/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── mcp_server.py        # MCP server configuration
│   ├── mcp_auth.py          # MCP API key authentication
│   ├── models/              # SQLAlchemy models
│   ├── routers/             # API route handlers
│   ├── schemas/             # Pydantic schemas
│   ├── core/                # Core utilities (security, config)
│   ├── db/                  # Database configuration
│   └── deps.py              # FastAPI dependencies
├── tests/                   # Test suite
├── alembic/                 # Database migrations
├── docker-compose.yml       # Docker services configuration
├── Dockerfile              # Application container
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

### Adding New Features

1. **Create Model** - Add SQLAlchemy model in `app/models/`
2. **Create Schema** - Add Pydantic schemas in `app/schemas/`
3. **Create Router** - Add API routes in `app/routers/`
4. **Register Router** - Import and include router in `app/main.py`
5. **Create Migration** - Generate Alembic migration
6. **Write Tests** - Add tests in `tests/`

### Database Migrations

```bash
# Create a new migration
docker-compose exec api alembic revision --autogenerate -m "Description"

# Apply migrations
docker-compose exec api alembic upgrade head

# Rollback migration
docker-compose exec api alembic downgrade -1
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://asana_user:asana_password@db:5432/asana_db` |
| `SECRET_KEY` | JWT secret key | `changeme` |
| `ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT token expiration | `30` |
| `ENABLE_MCP` | Enable MCP integration | `1` |
| `MCP_API_KEY` | API key for MCP server | `asana-mcp-secret-key-2025` |

## Documentation

- **[MCP_AUTH_GUIDE.md](MCP_AUTH_GUIDE.md)** - Complete guide for MCP API key authentication
- **[PROBLEMS.md](PROBLEMS.md)** - Known issues and solutions
- **[REPORT.md](REPORT.md)** - Development report and test results

## Security

- JWT-based authentication for API endpoints
- API key authentication for MCP server
- Password hashing with bcrypt
- Environment variable configuration
- Docker network isolation

**⚠️ Production Notes:**
- Change all default secrets and API keys
- Use HTTPS/TLS for all communications
- Store secrets in a secure secrets manager
- Implement rate limiting
- Enable CORS only for trusted origins
- Regularly rotate API keys and JWT secrets

## Troubleshooting

### Database Connection Issues

```bash
# Check if database is running
docker-compose ps

# View database logs
docker-compose logs db

# Restart database
docker-compose restart db
```

### API Not Responding

```bash
# Check API logs
docker-compose logs api

# Restart API
docker-compose restart api

# Rebuild if code changes aren't reflected
docker-compose up -d --build
```

### MCP Authentication Errors

See [MCP_AUTH_GUIDE.md](MCP_AUTH_GUIDE.md) for detailed troubleshooting.

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
