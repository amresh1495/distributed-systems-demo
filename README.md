# E-Commerce Microservices Platform

This project demonstrates a highly complicated distributed system for placing e-commerce orders, built with FastAPI and showcasing various microservices architecture concepts.

## Project Overview

The primary goal of this project is to simulate a realistic e-commerce backend with multiple microservices that interact to fulfill customer orders. It emphasizes backend architecture, inter-service communication, data management, resilience, and scalability rather than a polished UI.

## Core Microservices

The platform will consist of the following core microservices:

1.  **User Service (`user_service`)**:
    *   **Responsibilities**: Manages user registration, authentication (e.g., JWT), user profiles, and addresses.
    *   **Database Schema (Conceptual)**: `users` (id, username, email, hashed_password, full_name, created_at, updated_at), `addresses` (id, user_id, street, city, state, zip_code, country).
    *   **Key APIs**:
        *   `POST /api/v1/users/register`
        *   `POST /api/v1/users/login`
        *   `GET /api/v1/users/me` (requires auth)
        *   `PUT /api/v1/users/me` (requires auth)
        *   `POST /api/v1/users/me/addresses` (requires auth)
        *   `GET /api/v1/users/me/addresses` (requires auth)

2.  **Product Service (`product_service`)**:
    *   **Responsibilities**: Manages the product catalog, including product details (name, description, images, categories), pricing, and potentially different product variants. It does *not* manage real-time stock counts (that's Inventory Service).
    *   **Database Schema (Conceptual)**: `products` (id, name, description, price, category_id, created_at, updated_at), `categories` (id, name), `product_images` (id, product_id, image_url, alt_text).
    *   **Key APIs**:
        *   `POST /api/v1/products` (admin only)
        *   `GET /api/v1/products` (list with filtering/pagination)
        *   `GET /api/v1/products/{product_id}`
        *   `PUT /api/v1/products/{product_id}` (admin only)
        *   `DELETE /api/v1/products/{product_id}` (admin only)

3.  **Inventory Service (`inventory_service`)**:
    *   **Responsibilities**: Manages real-time stock levels for each product (and potentially product variants) across different warehouses or locations. Provides mechanisms to reserve and release stock.
    *   **Database Schema (Conceptual)**: `stock_items` (product_id, warehouse_id, quantity, reserved_quantity, last_updated).
    *   **Key APIs**:
        *   `GET /api/v1/inventory/{product_id}/stock`
        *   `POST /api/v1/inventory/reserve` (internal, called by Order Service)
        *   `POST /api/v1/inventory/release` (internal, called by Order Service on failure/cancellation)
        *   `POST /api/v1/inventory/fulfill` (internal, called on successful payment/shipment)
        *   `POST /api/v1/inventory/restock` (admin/supplier integration)

4.  **Order Service (`order_service`)**:
    *   **Responsibilities**: Orchestrates the order placement process. This involves:
        *   Receiving order requests from users.
        *   Communicating with User Service (user validation), Product Service (product details, prices), Inventory Service (stock reservation), and Payment Service.
        *   Managing the lifecycle of an order (e.g., PENDING, AWAITING_PAYMENT, PAID, SHIPPED, DELIVERED, CANCELLED, FAILED).
        *   Potentially using a Saga pattern for distributed transaction management.
    *   **Database Schema (Conceptual)**: `orders` (id, user_id, status, total_amount, created_at, updated_at), `order_items` (id, order_id, product_id, quantity, price_at_purchase).
    *   **Key APIs**:
        *   `POST /api/v1/orders` (creates a new order)
        *   `GET /api/v1/orders/{order_id}`
        *   `GET /api/v1/orders/my-orders` (user's orders)
        *   `POST /api/v1/orders/{order_id}/cancel`

5.  **Payment Service (`payment_service`)**:
    *   **Responsibilities**: Integrates with external payment gateways (e.g., Stripe, PayPal) to process payments. For this project, it will be a mocked service.
    *   **Database Schema (Conceptual)**: `payments` (id, order_id, amount, status, transaction_id, payment_method, created_at).
    *   **Key APIs**:
        *   `POST /api/v1/payments/process` (internal, called by Order Service)
        *   `GET /api/v1/payments/{order_id}/status`
        *   `POST /api/v1/payments/webhook` (simulated webhook from payment gateway)

6.  **Notification Service (`notification_service`)**:
    *   **Responsibilities**: Sends notifications to users (e.g., order confirmation, shipping updates) via various channels like email or SMS. This will be a mocked service.
    *   **Key APIs**:
        *   `POST /api/v1/notifications/send` (internal, typically triggered by events from other services)

## Communication & Integration

*   **Synchronous**: Primarily RESTful APIs (HTTP/S) for direct request/response interactions.
*   **Asynchronous**: A message broker (e.g., RabbitMQ or Kafka) will be planned for tasks like:
    *   Order Service notifying Notification Service.
    *   Inventory updates triggering cache invalidations in Product Service (if caching is implemented).
    *   Eventual consistency updates.
    *   *(Initially, direct HTTP calls might be used, with a plan to refactor to a message broker).*

## Database Strategy

*   Each microservice will have its own dedicated database to ensure loose coupling and independent scalability.
*   **PostgreSQL** is the preferred database system due to its robustness, support for transactions, and JSONB capabilities.
*   For local development, SQLite might be used for simplicity in the initial stages for some services, but the design should always target PostgreSQL.

## Key Architectural Concepts

This project aims to incorporate or demonstrate the following architectural concepts:

*   **Service Discovery**:
    *   **Local (Docker Compose)**: Services will discover each other using Docker's internal DNS, addressing services by their defined service names in `docker-compose.yml`.
    *   **Kubernetes**: Kubernetes' built-in DNS will be used for service discovery, where services are addressed by their K8s service names.
    *   *(No separate service discovery tool like Consul or etcd is planned for this project's scope, relying on platform features).*

*   **Load Balancing**:
    *   **Local (Docker Compose)**: The API Gateway (Nginx) can act as a basic load balancer if multiple instances of a service were run (though typically 1 instance per service in dev).
    *   **Kubernetes**: Handled by Kubernetes Services (e.g., LoadBalancer, NodePort, ClusterIP) and potentially an Ingress controller.

*   **API Gateway**:
    *   A single entry point (`api_gateway` using Nginx) for all client requests.
    *   Responsibilities: Request routing, basic rate limiting (potential), SSL termination (in production), and potentially aggregating some responses.

*   **Circuit Breaker Pattern**:
    *   **Plan**: To be implemented for critical inter-service calls (e.g., Order Service calling Payment or Inventory Service). This will prevent cascading failures by temporarily stopping requests to a failing service.
    *   **Implementation**: Could be a custom decorator or a lightweight library.

*   **Idempotency**:
    *   **Plan**: Critical operations, especially in Order and Payment services, will be designed to be idempotent. For example, processing a payment with the same transaction ID multiple times should result in only one actual payment.
    *   **Implementation**: Using unique request IDs, transaction tokens, or checking resource state before performing actions.

*   **Saga Pattern for Distributed Transactions**:
    *   **Plan**: The order creation process (involving Order, Inventory, and Payment services) is a prime candidate for the Saga pattern to ensure data consistency across services or proper compensation in case of failures.
    *   **Implementation**: Orchestration-based saga where the Order Service coordinates the transaction steps and compensating transactions.

*   **Distributed Tracing**:
    *   **Plan**: A correlation ID (e.g., `X-Request-ID` or `X-Correlation-ID`) will be generated at the API Gateway or by the first service hit, and propagated through all subsequent inter-service calls. This helps in tracking a request's journey across the system.
    *   **Implementation**: Middleware in each FastAPI service to extract/pass on the correlation ID. Full-fledged tracing with Jaeger/Zipkin is a potential future enhancement.

*   **Asynchronous Communication / Event-Driven Ideas**:
    *   As mentioned, a message broker (RabbitMQ/Kafka) is planned for non-critical path operations (e.g., sending notifications, certain types of cache invalidation). This helps decouple services and improve resilience.

*   **Security**:
    *   **Authentication**: JWT-based authentication for user-facing APIs originating from the User Service.
    *   **Service-to-Service**: Initially, communication within the trusted network (Docker network, K8s cluster). For enhanced security, API keys or mTLS could be considered in a production setup (likely out of scope for full implementation here).

*   **Configuration Management**:
    *   Services will be configured using environment variables, following the 12-factor app methodology. Docker Compose and Kubernetes manifests will manage these.

*   **CQRS (Command Query Responsibility Segregation) & Event Sourcing**:
    *   **Consideration**: These are advanced patterns.
        *   **CQRS**: Could be beneficial for services like the Product Service (separate models/paths for high-volume reads of product catalog vs. writes/updates).
        *   **Event Sourcing**: Storing all state changes as a sequence of events could be powerful for auditing and rebuilding state, but adds complexity.
    *   **Scope**: While their benefits are noted, full implementation might be out of scope for the initial version to manage complexity. They will be discussed as potential architectural evolutions.

## Technology Stack

*   **Backend Framework**: FastAPI (Python)
*   **Database**: PostgreSQL (primary), SQLite (for initial local dev on some services if needed)
*   **Data Access**: SQLModel (ORM)
*   **Containerization**: Docker
*   **Local Orchestration**: Docker Compose
*   **Deployment Orchestration**: Kubernetes
*   **API Gateway**: Nginx
*   **Messaging (Planned)**: RabbitMQ or Kafka (initially direct HTTP, to be refactored)
*   **Frontend**: Basic HTML, CSS, JavaScript (for demonstration)

## Project Structure

```
.
├── docker-compose.yml          # Docker Compose for local development
├── README.md                   # This file
└── ecommerce_platform/
    ├── api_gateway/            # Nginx configuration and Dockerfile
    │   ├── Dockerfile
    │   └── nginx.conf
    ├── frontend/               # Basic HTML, CSS, JS for UI
    │   ├── app.js
    │   ├── index.html
    │   └── style.css
    ├── kubernetes/             # Kubernetes manifests
    │   ├── 00-namespace.yml
    │   ├── ... (all k8s yamls)
    │   └── README.md
    └── services/               # Individual microservices
        ├── user_service/
        │   ├── app/            # Python application code
        │   │   ├── main.py
        │   │   ├── models.py
        │   │   ├── crud.py
        │   │   ├── api.py
        │   │   └── db.py
        │   ├── tests/          # Tests for the service
        │   │   ├── __init__.py
        │   │   ├── conftest.py
        │   │   └── test_*.py
        │   ├── Dockerfile
        │   └── requirements.txt
        ├── product_service/
        │   └── ... (similar structure)
        └── ... (other services)
```

## Setup and Running Locally (Docker Compose)

1.  **Prerequisites**:
    *   Docker Desktop or Docker Engine with Docker Compose installed.
    *   Git (to clone the repository).

2.  **Clone the Repository**:
    ```bash
    git clone <repository_url>
    cd ecommerce_platform
    ```

3.  **Environment Variables**:
    *   Some services might require environment variables (e.g., JWT secrets). Check the `docker-compose.yml` file. For User Service, you might need to set `JWT_SECRET_KEY` and `ALGORITHM` if not using defaults provided in comments.
    *   Database credentials are set in `docker-compose.yml` for `postgres_db` and used by services.

4.  **Build and Run Services**:
    ```bash
    docker-compose up --build -d
    ```
    *   `--build`: Forces a build of the images.
    *   `-d`: Runs containers in detached mode.

5.  **Database Initialization**:
    *   The `postgres_db` service will start, and PostgreSQL will initialize.
    *   Each service, upon its first run with a new database, will need to create its specific database (e.g., `user_service_db`). The application code (specifically `db.py` and `main.py` startup events) should handle the creation of tables using `SQLModel.metadata.create_all(engine)`.
    *   **Important**: The `postgres_db` service in `docker-compose.yml` initializes with a main database (`ecommerce_main_db`). However, each microservice is configured to use its own specific database (e.g., `user_service_db`, `product_service_db`).
    *   The standard `postgres` Docker image will only automatically create the database specified by the `POSTGRES_DB` environment variable at startup. It will **not** automatically create `user_service_db`, `product_service_db`, etc.
    *   **Action Required for Docker Compose**:
        1.  **Option 1 (Recommended for simplicity): Grant `CREATEDB` privilege to `ecommerce_user`**. After `docker-compose up -d` is running, you can exec into the postgres container and grant the privilege:
            ```bash
            docker-compose exec postgres_db psql -U ecommerce_user -c "ALTER USER ecommerce_user CREATEDB;"
            # You might need to connect as the default 'postgres' superuser if 'ecommerce_user' initially lacks rights
            # docker-compose exec postgres_db psql -U postgres -c "ALTER USER ecommerce_user CREATEDB;"
            ```
            Once `ecommerce_user` has `CREATEDB` privilege, the services *should* be able to create their respective databases upon first connection if their database driver/ORM setup attempts it (psycopg2 usually requires DB to exist). SQLModel's `create_all` creates tables, not databases. The application's `db.py` `ensure_database_connection` attempts to connect; if the DB doesn't exist, this connection will fail.
        2.  **Option 2: Manually create databases**. After `docker-compose up -d`, exec into the postgres container and create each database:
            ```bash
            docker-compose exec postgres_db psql -U ecommerce_user -d ecommerce_main_db -c "CREATE DATABASE user_service_db;"
            docker-compose exec postgres_db psql -U ecommerce_user -d ecommerce_main_db -c "CREATE DATABASE product_service_db;"
            docker-compose exec postgres_db psql -U ecommerce_user -d ecommerce_main_db -c "CREATE DATABASE inventory_service_db;"
            # ... and so on for other services.
            ```
            (Connect to `ecommerce_main_db` or `postgres` to issue `CREATE DATABASE` commands).
    *   Once the individual databases exist and the user has rights, `SQLModel.metadata.create_all(engine)` in each service's `db.py` (called on startup) will create the necessary tables within that database.

6.  **Accessing Services**:
    *   **API Gateway**: `http://localhost:80` (or the port mapped in `docker-compose.yml` for `api_gateway`).
    *   **Individual Services (if ports directly exposed for debugging)**:
        *   User Service: `http://localhost:8001`
        *   Product Service: `http://localhost:8002`
        *   And so on for other services.
    *   **Frontend Demo**: Access `http://localhost` (served by the API Gateway).

7.  **API Documentation (Swagger UI)**:
    *   Each FastAPI service will provide interactive API documentation:
        *   User Service: `http://localhost:8001/docs`
        *   Product Service: `http://localhost:8002/docs`
        *   ...etc.
    *   Via API Gateway:
        *   User Service Docs: `http://localhost/api/users/docs` (Nginx rewrite rule must correctly handle this path to the service's `/docs` endpoint - this may require specific Nginx location blocks for `/api/*/docs`). *Currently, the Nginx config might not explicitly support this sub-path routing to the docs endpoint of backend services; this is a TODO to verify/implement.*

8.  **Stopping Services**:
    ```bash
    docker-compose down
    ```
    *   To remove volumes (like PostgreSQL data): `docker-compose down -v`

## Deploying to Kubernetes

1.  **Prerequisites**:
    *   A running Kubernetes cluster (e.g., Minikube, Kind, GKE, EKS, AKS).
    *   `kubectl` configured to communicate with your cluster.
    *   A container registry (like Docker Hub, GCR, ECR) where your built service images are pushed. The manifest files use placeholder image names like `your-repo/user-service:latest`. You'll need to replace these with your actual image paths.

2.  **Build and Push Docker Images**:
    *   For each service in `services/` and for `api_gateway/`:
        ```bash
        # Example for user_service
        cd services/user_service
        docker build -t your-registry/user-service:v1.0.0 .
        docker push your-registry/user-service:v1.0.0
        cd ../..
        ```
    *   **Important for API Gateway**: The `api_gateway/Dockerfile` needs to be updated to copy the `frontend` static files into the image (e.g., `COPY ../frontend /var/www/frontend`) so Nginx can serve them as configured in `kubernetes/30-api-gateway.yml`.

3.  **Apply Namespace**:
    ```bash
    kubectl apply -f kubernetes/00-namespace.yml
    ```

4.  **Create Secrets**:
    *   The `kubernetes/02-secrets.yml` file contains base64 encoded example secrets. **For production, generate your own strong secrets and manage them securely (e.g., using HashiCorp Vault, Sealed Secrets, or cloud provider's secret management).**
    *   Update the base64 values in `02-secrets.yml` with your actual encoded secrets.
    *   Apply the secrets:
        ```bash
        kubectl apply -f kubernetes/02-secrets.yml
        ```

5.  **Create ConfigMap**:
    ```bash
    kubectl apply -f kubernetes/01-configmap.yml
    ```

6.  **Deploy PostgreSQL**:
    ```bash
    kubectl apply -f kubernetes/10-postgres-statefulset.yml
    ```
    *   Wait for PostgreSQL to be ready: `kubectl get pods -n ecommerce-ns -l app=postgres -w` (Wait until status is Running and Ready 1/1).

7.  **Run PostgreSQL DB Initialization Job**:
    *   This job creates the necessary databases for each service.
    *   **Privilege Requirement**: The PostgreSQL user defined in `ecommerce-secrets` (e.g., `ecommerce_user`) must have `CREATEDB` privileges. If not, this job will fail. You might need to grant this privilege manually by connecting to PostgreSQL as a superuser (e.g., the default `postgres` user) after the StatefulSet is running:
        ```bash
        # Example: Port-forward to postgres pod if needed to connect locally
        # kubectl port-forward pod/postgres-db-0 5432:5432 -n ecommerce-ns
        # Then connect using psql and run:
        # ALTER USER ecommerce_user CREATEDB;
        ```
    *   Apply the job:
        ```bash
        kubectl apply -f kubernetes/11-postgres-init-job.yml
        ```
    *   Check job status: `kubectl get jobs -n ecommerce-ns -w` and logs: `kubectl logs -f job/postgres-db-init -n ecommerce-ns`.

8.  **Deploy Microservices**:
    *   Deploy each service one by one (or all at once). Ensure image paths in the YAML files are correct.
        ```bash
        kubectl apply -f kubernetes/20-user-service.yml
        kubectl apply -f kubernetes/21-product-service.yml
        kubectl apply -f kubernetes/22-inventory-service.yml
        kubectl apply -f kubernetes/23-order-service.yml
        kubectl apply -f kubernetes/24-payment-service.yml
        kubectl apply -f kubernetes/25-notification-service.yml
        ```
    *   Check pod status: `kubectl get pods -n ecommerce-ns -w`

9.  **Deploy API Gateway**:
    *   The API Gateway Nginx configuration is in `kubernetes/30-api-gateway.yml` as a ConfigMap.
    ```bash
    kubectl apply -f kubernetes/30-api-gateway.yml
    ```

10. **Accessing the Application**:
    *   If the `api-gateway-svc` is of type `LoadBalancer`, Kubernetes will provision an external IP. Find it:
        ```bash
        kubectl get svc api-gateway-svc -n ecommerce-ns
        ```
        (Look for `EXTERNAL-IP`). Access the app at `http://<EXTERNAL-IP>`.
    *   If using Minikube and `LoadBalancer` type, you might need to run:
        ```bash
        minikube service api-gateway-svc -n ecommerce-ns
        ```
        This will open the service URL in your browser.
    *   If `api-gateway-svc` is `NodePort`, find the NodePort and your cluster's node IP:
        `http://<NodeIP>:<NodePort>`.

11. **API Documentation (Swagger UI) in Kubernetes**:
    *   Once the API Gateway is accessible via its external IP/port:
    *   Accessing individual service docs via gateway (e.g., `http://<EXTERNAL-IP>/api/users/docs`) depends on Nginx correctly proxying these paths. The current Nginx config in K8s (`30-api-gateway.yml`) uses rewrite rules like `rewrite ^/api/users(/.*)$ /api/v1/users$1 break;`. This should correctly map `/api/users/docs` to `user-service-svc:8000/api/v1/users/docs`.
    *   Each FastAPI service (e.g., User service at `user-service-svc:8000`) will host its Swagger UI at `/docs` relative to its root. The API gateway routes `/api/users/*` to the user service's `/api/v1/users/*`. So, `/api/users/docs` should be routed to `/api/v1/users/docs` on the user service. This needs careful verification.

## API Documentation Strategy

*   Each FastAPI microservice automatically generates OpenAPI documentation (JSON schema at `/openapi.json`) and provides Swagger UI (`/docs`) and ReDoc (`/redoc`) interfaces.
*   These can be accessed per service (if ports are exposed locally or via port-forwarding in K8s) or through the API Gateway if routes are configured.
*   The API Gateway (`api_gateway/nginx.conf` and its K8s ConfigMap version) is responsible for routing external requests like `https://yourdomain.com/api/users/...` to the appropriate `user_service` endpoints like `http://user_service:8000/api/v1/users/...`.
*   A central, aggregated API documentation portal is not part of this project's initial scope but could be a future enhancement (e.g., using tools that can combine multiple OpenAPI schemas).

*(This README will be further refined as services are implemented and tested.)*
