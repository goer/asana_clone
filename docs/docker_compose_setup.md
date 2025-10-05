

Of course. Using Docker Compose is an excellent way to streamline development, ensuring that all developers (and CI/CD systems) work with an identical environment.

Here are the instructions and configuration files to set up the FastAPI Asana Clone project using Docker Compose.

---

### **Objective**

Containerize the FastAPI application and its PostgreSQL database using Docker and Docker Compose for a consistent and portable development environment.

---

### **Phase 1: Update Project Structure**

Add the following files to the root of your `asana-clone-api` project:

```
asana-clone-api/
├── .dockerignore
├── .env
├── docker-compose.yml
├── Dockerfile
├── alembic.ini
├── alembic/
├── app/
│   └── ... (rest of the app)
└── requirements.txt
```

---

### **Phase 2: Create the Dockerfile**

This file defines the steps to build the container image for your FastAPI application.

**`Dockerfile`**
```dockerfile
# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# --no-cache-dir reduces image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container at /app
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
# Note: We will override this with --reload in docker-compose for development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### **Phase 3: Create the `.dockerignore` File**

This file prevents unnecessary files from being copied into your Docker image, keeping it small and fast to build.

**`.dockerignore`**
```
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
.venv/
venv/
env/
ENV/

# Environment Variables
.env

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Git
.git/
.gitignore

# Alembic (optional, if you want to manage versions outside the image)
# alembic/versions/*
```

---

### **Phase 4: Configure `docker-compose.yml`**

This is the core file that defines and orchestrates your services (the API and the database).

**`docker-compose.yml`**
```yaml
version: '3.8'

services:
  # The PostgreSQL Database Service
  db:
    image: postgres:15-alpine
    volumes:
      # Persist database data between container restarts
      - postgres_data:/var/lib/postgresql/data/
    env_file:
      - .env
    ports:
      # Expose the database to the host for easy access with a DB client
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 5

  # The FastAPI Application Service
  api:
    build: . # Build the image from the Dockerfile in the current directory
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      # Mount the source code for live-reloading
      - .:/app
    ports:
      # Map the container port to the host port
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy # Wait for the db service to be healthy before starting

# Define the named volume for data persistence
volumes:
  postgres_data:
```

---

### **Phase 5: Update Environment Variables**

Modify your `.env` file to use the Docker service names for inter-service communication.

**`.env`**
```
# --- Database Configuration ---
# The hostname 'db' matches the service name in docker-compose.yml
DATABASE_URL=postgresql://asana_user:asana_password@db:5432/asana_db

# These are used by the postgres image itself
POSTGRES_USER=asana_user
POSTGRES_PASSWORD=asana_password
POSTGRES_DB=asana_db

# --- Application Security ---
SECRET_KEY=your-super-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```
**Key Change:** Notice the `DATABASE_URL` now uses `db` as the hostname. Docker Compose creates a network where services can reach each other using their service names.

---

### **Phase 6: The Docker Development Workflow**

Now you can manage your entire application stack with simple commands.

1.  **Build and Start the Services**
    Run this command from the root directory. It will build the `api` image (if it doesn't exist) and start both the `db` and `api` containers in the background.
    ```bash
    docker-compose up --build -d
    ```
    *   `--build`: Forces a rebuild of the `api` image.
    *   `-d`: Detached mode (runs in the background).

2.  **Run Database Migrations**
    The containers are running, but the database is empty. You need to run Alembic inside the `api` container to create the tables.
    ```bash
    docker-compose exec api alembic upgrade head
    ```
    *   `docker-compose exec api`: Executes a command inside the running `api` container.
    *   `alembic upgrade head`: The Alembic command to apply all migrations.

3.  **Access the Application**
    *   **API:** Your FastAPI application is now running at `http://127.0.0.1:8000`.
    *   **Interactive Docs:** `http://127.0.0.1:8000/docs`
    *   **Database:** You can connect to the PostgreSQL database at `localhost:5432` using a GUI client (like DBeaver, TablePlus, or pgAdmin) with the credentials from your `.env` file.

4.  **View Logs**
    To see the logs from both services:
    ```bash
    docker-compose logs -f
    ```
    To see logs for just one service:
    ```bash
    docker-compose logs -f api
    ```

5.  **Stop the Services**
    To stop and remove the containers:
    ```bash
    docker-compose down
    ```
    The `postgres_data` volume will persist, so your database data is safe. If you want to remove the volume as well (to start with a completely fresh database), use `docker-compose down -v`.

### **Summary of Benefits**

*   **One-Command Setup:** Any new developer can clone the repo and run `docker-compose up --build -d` to get a fully working environment.
*   **Consistency:** Eliminates "it works on my machine" issues.
*   **Isolation:** The application and its dependencies are isolated from your host machine.
*   **Live Reloading:** Code changes on your host are instantly reflected in the running container thanks to the volume mount and `--reload` flag.