

Of course. Here is a comprehensive OpenAPI 3.0 specification for an Asana clone application.

This spec is designed to be RESTful, follows modern API design principles, and maps directly to the database schema we previously created. It includes authentication, core CRUD operations for all major entities, and more advanced features like filtering and pagination.

### Key Design Choices in this API

*   **RESTful Endpoints:** Uses standard HTTP verbs (`GET`, `POST`, `PATCH`, `DELETE`) and resource-based URLs.
*   **Bearer Token Authentication:** Uses a standard `Authorization: Bearer <token>` header for securing endpoints. The token would be a JWT issued from a `/auth/login` endpoint.
*   **Nested Resources:** Endpoints like `GET /projects/{projectId}/tasks` provide intuitive access to related data.
*   **Rich Filtering:** The `GET /tasks` endpoint includes query parameters for powerful filtering, a core feature of Asana.
*   **Data Enrichment:** Schemas for objects like `Task` and `Project` include nested objects (e.g., `assignee: { id, name }`) instead of just IDs, reducing the number of API calls needed by the client.
*   **Pagination:** List endpoints use `limit` and `offset` for pagination and return metadata about the total number of items.
*   **OpenAPI Components:** Uses `components/schemas` for reusable data models, keeping the spec DRY (Don't Repeat Yourself).

---

### OpenAPI 3.0 Specification (YAML)

```yaml
openapi: 3.0.3
info:
  title: Asana Clone API
  description: A RESTful API for a project management application similar to Asana.
  version: 1.0.0
servers:
  - url: https://api.asana-clone.com/v1
    description: Production Server
  - url: http://localhost:3000/v1
    description: Development Server

tags:
  - name: Authentication
    description: Operations for user authentication and registration.
  - name: Users
    description: Operations about users.
  - name: Workspaces
    description: Operations for managing workspaces.
  - name: Projects
    description: Operations for managing projects.
  - name: Tasks
    description: Operations for managing tasks and subtasks.
  - name: Sections
    description: Operations for managing project sections.
  - name: Comments
    description: Operations for managing task comments.

paths:
  /auth/register:
    post:
      tags:
        - Authentication
      summary: Register a new user
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - email
                - name
                - password
              properties:
                email:
                  type: string
                  format: email
                name:
                  type: string
                password:
                  type: string
                  format: password
      responses:
        '201':
          description: User registered successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AuthResponse'
        '400':
          $ref: '#/components/responses/BadRequest'
        '409':
          description: Email already exists

  /auth/login:
    post:
      tags:
        - Authentication
      summary: Log in a user
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - email
                - password
              properties:
                email:
                  type: string
                  format: email
                password:
                  type: string
                  format: password
      responses:
        '200':
          description: Login successful
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AuthResponse'
        '401':
          $ref: '#/components/responses/Unauthorized'

  /users/me:
    get:
      tags:
        - Users
      summary: Get the current user's profile
      security:
        - bearerAuth: []
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'
        '401':
          $ref: '#/components/responses/Unauthorized'

  /workspaces:
    get:
      tags:
        - Workspaces
      summary: Get all workspaces for the current user
      security:
        - bearerAuth: []
      responses:
        '200':
          description: A list of workspaces
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Workspace'
        '401':
          $ref: '#/components/responses/Unauthorized'
    post:
      tags:
        - Workspaces
      summary: Create a new workspace
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/WorkspaceInput'
      responses:
        '201':
          description: Workspace created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Workspace'
        '400':
          $ref: '#/components/responses/BadRequest'

  /projects:
    get:
      tags:
        - Projects
      summary: Get projects in a workspace
      security:
        - bearerAuth: []
      parameters:
        - name: workspace_id
          in: query
          required: true
          schema:
            type: integer
      responses:
        '200':
          description: A list of projects
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Project'
        '401':
          $ref: '#/components/responses/Unauthorized'
    post:
      tags:
        - Projects
      summary: Create a new project
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ProjectInput'
      responses:
        '201':
          description: Project created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Project'
        '400':
          $ref: '#/components/responses/BadRequest'

  /projects/{projectId}:
    get:
      tags:
        - Projects
      summary: Get a single project
      security:
        - bearerAuth: []
      parameters:
        - $ref: '#/components/parameters/ProjectId'
      responses:
        '200':
          description: Project details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Project'
        '404':
          $ref: '#/components/responses/NotFound'
    patch:
      tags:
        - Projects
      summary: Update a project
      security:
        - bearerAuth: []
      parameters:
        - $ref: '#/components/parameters/ProjectId'
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ProjectInput'
      responses:
        '200':
          description: Project updated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Project'
        '404':
          $ref: '#/components/responses/NotFound'

  /tasks:
    get:
      tags:
        - Tasks
      summary: Get tasks with optional filtering
      security:
        - bearerAuth: []
      parameters:
        - name: project_id
          in: query
          schema:
            type: integer
        - name: assignee
          in: query
          description: 'Filter by assignee. Use "me" for the current user.'
          schema:
            type: string
        - name: completed_since
          in: query
          description: 'Filter for tasks completed since this timestamp.'
          schema:
            type: string
            format: date-time
        - name: limit
          in: query
          schema:
            type: integer
            default: 20
        - name: offset
          in: query
          schema:
            type: integer
            default: 0
      responses:
        '200':
          description: A paginated list of tasks
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PaginatedTasks'
        '401':
          $ref: '#/components/responses/Unauthorized'
    post:
      tags:
        - Tasks
      summary: Create a new task
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/TaskInput'
      responses:
        '201':
          description: Task created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Task'
        '400':
          $ref: '#/components/responses/BadRequest'

  /tasks/{taskId}:
    get:
      tags:
        - Tasks
      summary: Get a single task
      security:
        - bearerAuth: []
      parameters:
        - $ref: '#/components/parameters/TaskId'
      responses:
        '200':
          description: Task details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Task'
        '404':
          $ref: '#/components/responses/NotFound'
    patch:
      tags:
        - Tasks
      summary: Update a task
      security:
        - bearerAuth: []
      parameters:
        - $ref: '#/components/parameters/TaskId'
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/TaskInput'
      responses:
        '200':
          description: Task updated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Task'
        '404':
          $ref: '#/components/responses/NotFound'
    delete:
      tags:
        - Tasks
      summary: Delete a task
      security:
        - bearerAuth: []
      parameters:
        - $ref: '#/components/parameters/TaskId'
      responses:
        '204':
          description: Task deleted
        '404':
          $ref: '#/components/responses/NotFound'

  /tasks/{taskId}/comments:
    get:
      tags:
        - Comments
      summary: Get comments for a task
      security:
        - bearerAuth: []
      parameters:
        - $ref: '#/components/parameters/TaskId'
      responses:
        '200':
          description: A list of comments
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Comment'
    post:
      tags:
        - Comments
      summary: Add a comment to a task
      security:
        - bearerAuth: []
      parameters:
        - $ref: '#/components/parameters/TaskId'
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - text
              properties:
                text:
                  type: string
      responses:
        '201':
          description: Comment added
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Comment'

components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

  parameters:
    ProjectId:
      name: projectId
      in: path
      required: true
      schema:
        type: integer
    TaskId:
      name: taskId
      in: path
      required: true
      schema:
        type: integer

  schemas:
    User:
      type: object
      properties:
        id:
          type: integer
        email:
          type: string
        name:
          type: string
        created_at:
          type: string
          format: date-time

    Workspace:
      type: object
      properties:
        id:
          type: integer
        name:
          type: string
        owner:
          $ref: '#/components/schemas/User'
        created_at:
          type: string
          format: date-time

    WorkspaceInput:
      type: object
      required:
        - name
      properties:
        name:
          type: string

    Project:
      type: object
      properties:
        id:
          type: integer
        name:
          type: string
        description:
          type: string
        owner:
          $ref: '#/components/schemas/User'
        workspace:
          $ref: '#/components/schemas/Workspace'
        created_at:
          type: string
          format: date-time

    ProjectInput:
      type: object
      required:
        - name
        - workspace_id
      properties:
        name:
          type: string
        description:
          type: string
        workspace_id:
          type: integer

    Task:
      type: object
      properties:
        id:
          type: integer
        name:
          type: string
        description:
          type: string
        completed:
          type: boolean
        due_date:
          type: string
          format: date-time
        assignee:
          $ref: '#/components/schemas/User'
        project:
          $ref: '#/components/schemas/Project'
        parent_task:
          type: object
          nullable: true
          properties:
            id:
              type: integer
            name:
              type: string
        created_at:
          type: string
          format: date-time

    TaskInput:
      type: object
      required:
        - name
      properties:
        name:
          type: string
        description:
          type: string
        project_id:
          type: integer
        assignee_id:
          type: integer
        parent_task_id:
          type: integer
        due_date:
          type: string
          format: date-time
        completed:
          type: boolean

    Comment:
      type: object
      properties:
        id:
          type: integer
        text:
          type: string
        author:
          $ref: '#/components/schemas/User'
        created_at:
          type: string
          format: date-time

    AuthResponse:
      type: object
      properties:
        user:
          $ref: '#/components/schemas/User'
        token:
          type: string

    PaginatedTasks:
      type: object
      properties:
        data:
          type: array
          items:
            $ref: '#/components/schemas/Task'
        pagination:
          type: object
          properties:
            total:
              type: integer
            limit:
              type: integer
            offset:
              type: integer

    Error:
      type: object
      properties:
        message:
          type: string
        errors:
          type: array
          items:
            type: string

  responses:
    BadRequest:
      description: Bad Request
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    Unauthorized:
      description: Unauthorized
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    NotFound:
      description: Resource Not Found
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'

```