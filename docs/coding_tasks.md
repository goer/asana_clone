

Of course. Here are comprehensive instructions for an AI agent to build the Asana clone backend using Python and FastAPI, based on the previously generated PostgreSQL schema and OpenAPI specification.

---

### **Objective**

Your task is to build a RESTful API for an Asana clone using Python and the FastAPI framework. The API must adhere to the provided OpenAPI 3.0 specification and interact with a PostgreSQL database defined by the provided schema.

### **General Guidelines**

1.  **Follow the Structure:** Adhere to the project structure and phase-by-phase plan outlined below.
2.  **Type Hinting:** Use Python type hints rigorously. FastAPI and Pydantic rely on them heavily.
3.  **Code Organization:** Keep code modular. Separate concerns: database models, Pydantic schemas, API logic (routers), and core utilities (security, config).
4.  **Pydantic v2:** Use Pydantic V2 syntax. For SQLAlchemy model compatibility, use `model_config = {"from_attributes": True}` instead of the deprecated `orm_mode = True`.

---

### **Phase 1: Project Setup & Dependencies**

1.  **Create Project Directory:**
    ```
    asana-clone-api/
    └── venv/
    ```

2.  **Set up Virtual Environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install "fastapi[all]" uvicorn sqlalchemy psycopg2-binary alembic python-jose[cryptography] passlib[bcrypt]
    ```
    *   `fastapi`: The web framework.
    *   `uvicorn`: The ASGI server to run the app.
    *   `sqlalchemy`: The ORM for database interaction.
    *   `psycopg2-binary`: The PostgreSQL driver.
    *   `alembic`: For database migrations.
    *   `python-jose`: For JWT (JSON Web Token) creation and verification.
    *   `passlib`: For secure password hashing.

4.  **Create Initial File Structure:**
    ```
    asana-clone-api/
    ├── alembic/
    ├── app/
    │   ├── __init__.py
    │   ├── core/
    │   │   ├── __init__.py
    │   │   ├── config.py
    │   │   └── security.py
    │   ├── db/
    │   │   ├── __init__.py
    │   │   ├── database.py
    │   │   └── session.py
    │   ├── models/
    │   │   ├── __init__.py
    │   │   ├── user.py
    │   │   ├── workspace.py
    │   │   ├── project.py
    │   │   ├── task.py
    │   │   └── comment.py
    │   ├── schemas/
    │   │   ├── __init__.py
    │   │   ├── user.py
    │   │   ├── workspace.py
    │   │   ├── project.py
    │   │   ├── task.py
    │   │   └── comment.py
    │   ├── routers/
    │   │   ├── __init__.py
    │   │   ├── auth.py
    │   │   ├── users.py
    │   │   ├── workspaces.py
    │   │   ├── projects.py
    │   │   ├── tasks.py
    │   │   └── comments.py
    │   ├── deps.py
    │   └── main.py
    ├── .env
    ├── alembic.ini
    └── requirements.txt
    ```

---

### **Phase 2: Database & ORM Setup**

1.  **Environment Variables (`.env`):**
    Create a `.env` file in the root directory.
    ```
    DATABASE_URL=postgresql://user:password@host:port/dbname
    SECRET_KEY=your-super-secret-key-here
    ALGORITHM=HS256
    ACCESS_TOKEN_EXPIRE_MINUTES=30
    ```

2.  **Core Configuration (`app/core/config.py`):**
    Read the `.env` file using Pydantic's `BaseSettings`.
    ```python
    from pydantic_settings import BaseSettings

    class Settings(BaseSettings):
        DATABASE_URL: str
        SECRET_KEY: str
        ALGORITHM: str = "HS256"
        ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

        model_config = {"env_file": ".env"}

    settings = Settings()
    ```

3.  **Database Session (`app/db/session.py`):**
    Create a factory for database sessions.
    ```python
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings

    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    ```

4.  **SQLAlchemy Models (`app/models/`):**
    Translate the provided PostgreSQL schema into SQLAlchemy model classes.
    *   Create a base class in `app/models/__init__.py`.
    *   Create one file per model (e.g., `user.py`, `project.py`).
    *   **Example (`app/models/user.py`):**
        ```python
        from sqlalchemy import Boolean, Column, Integer, String, DateTime
        from sqlalchemy.sql import func
        from app.db.database import Base

        class User(Base):
            __tablename__ = "users"

            id = Column(Integer, primary_key=True, index=True)
            email = Column(String, unique=True, index=True, nullable=False)
            name = Column(String, nullable=False)
            password_hash = Column(String, nullable=False)
            created_at = Column(DateTime(timezone=True), server_default=func.now())
            updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
        ```
    *   Define all relationships (`relationship`, `ForeignKey`) as specified in the schema. For example, `Project` should have a `owner_id` foreign key and a `relationship` to the `User` model.

5.  **Alembic Setup for Migrations:**
    *   Run `alembic init alembic`.
    *   In `alembic.ini`, set `sqlalchemy.url =` to your `DATABASE_URL`.
    *   In `alembic/env.py`, make sure `target_metadata` is imported from your models: `from app.models import Base; target_metadata = Base.metadata`.
    *   Create the first migration: `alembic revision --autogenerate -m "Initial schema"`
    *   Apply the migration to the DB: `alembic upgrade head`

---

### **Phase 3: Authentication & Security**

1.  **Security Utilities (`app/core/security.py`):**
    Implement password hashing and JWT handling.
    ```python
    from datetime import datetime, timedelta
    from jose import JWTError, jwt
    from passlib.context import CryptContext
    from app.core.config import settings

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def verify_password(plain_password, hashed_password):
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(password):
        return pwd_context.hash(password)

    def create_access_token(data: dict, expires_delta: timedelta = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    ```

2.  **Dependency for Current User (`app/deps.py`):**
    Create a FastAPI dependency to extract and verify the JWT token from requests.
    ```python
    from fastapi import Depends, HTTPException, status
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from jose import JWTError, jwt
    from sqlalchemy.orm import Session
    from app.core.config import settings
    from app.db.session import get_db
    from app.models.user import User

    security = HTTPBearer()

    def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id: int = payload.get("sub")
            if user_id is None:
                raise credentials_exception
        except JWTError:
            raise credentials_exception
        
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise credentials_exception
        return user
    ```

---

### **Phase 4: API Endpoint Implementation**

1.  **Pydantic Schemas (`app/schemas/`):**
    For each model, create corresponding Pydantic schemas for request/response bodies.
    *   **Base Schema:** Contains common fields.
    *   **Create Schema:** For `POST` requests. Inherits from Base.
    *   **Update Schema:** For `PATCH` requests. All fields optional.
    *   **Response Schema:** For `GET` responses. Use `ConfigDict(from_attributes=True)`. Include nested objects where the OpenAPI spec requires them (e.g., `Project` schema should include an `owner: User | None` field).

    *   **Example (`app/schemas/user.py`):**
        ```python
        from pydantic import BaseModel, EmailStr
        from typing import Optional
        from datetime import datetime

        class UserBase(BaseModel):
            email: EmailStr
            name: str

        class UserCreate(UserBase):
            password: str

        class User(UserBase):
            id: int
            created_at: datetime

            model_config = ConfigDict(from_attributes=True)

        class Token(BaseModel):
            access_token: str
            token_type: str
        ```

2.  **API Routers (`app/routers/`):**
    Implement the endpoints for each resource group as defined in the OpenAPI spec.

    *   **Authentication (`app/routers/auth.py`):**
        *   `POST /auth/register`: Hash the password, create a `User` model instance, save to DB.
        *   `POST /auth/login`: Verify user exists, verify password, create JWT, return `Token` schema.

    *   **Projects (`app/routers/projects.py`):**
        *   `GET /projects`: Accept `workspace_id` as a query param. Use `get_current_user` dependency to ensure authentication. Query the DB for projects the user has access to.
        *   `POST /projects`: Accept `ProjectCreate` schema. Create a new `Project` in the DB.
        *   `GET /projects/{id}`: Retrieve a single project. Return 404 if not found.
        *   `PATCH /projects/{id}`: Accept `ProjectUpdate` schema. Fetch the project, update fields, save.
        *   `DELETE /projects/{id}`: Fetch and delete the project.

    *   **Repeat this pattern for `tasks`, `workspaces`, `comments`, etc.**
    *   **For filtering (`GET /tasks`):** Use query parameters in the function signature (e.g., `assignee: Optional[str] = None`, `project_id: Optional[int] = None`). Build the SQLAlchemy query dynamically based on these parameters.
    *   **For pagination:** Add `limit: int = 20`, `offset: int = 0` query parameters to list endpoints.

3.  **Main Application (`app/main.py`):**
    Tie everything together.
    ```python
    from fastapi import FastAPI
    from app.routers import auth, users, workspaces, projects, tasks, comments

    app = FastAPI(title="Asana Clone API")

    app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
    app.include_router(users.router, prefix="/users", tags=["Users"])
    app.include_router(workspaces.router, prefix="/workspaces", tags=["Workspaces"])
    # ... include all other routers

    @app.get("/")
    def read_root():
        return {"message": "Welcome to the Asana Clone API"}
    ```

---

### **Phase 5: Running the Application**

1.  **Ensure your PostgreSQL server is running and the database exists.**
2.  **Run database migrations:**
    ```bash
    alembic upgrade head
    ```
3.  **Start the FastAPI server with Uvicorn:**
    ```bash
    uvicorn app.main:app --reload
    ```
4.  **Access the interactive API docs:** Open your browser to `http://127.0.0.1:8000/docs`. This will automatically generate the Swagger UI from your code, which should match the provided OpenAPI spec. Use it to test your endpoints.