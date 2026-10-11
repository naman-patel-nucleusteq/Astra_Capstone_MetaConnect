# MetaConnect

MetaConnect is a metadata extraction and management platform. In simple words, it helps you connect to data sources, inspect their databases and tables, and track pipeline runs that collect metadata from those sources.

This project is built for a modern data catalog workflow:

- connect to a source such as Snowflake or Pinot
- save the connection details securely
- pull metadata such as databases, schemas, tables, and columns
- view the metadata in a dashboard and explorer UI
- create and schedule ingestion pipelines
- monitor background pipeline runs through Airflow
- use Keycloak-based login for access control

At a high level, the project has three main parts:

1. Frontend UI: React app for dashboards, connection setup, metadata browsing, and pipeline monitoring
2. Backend API: FastAPI app that stores metadata, handles authentication, and talks to connectors
3. Data orchestration stack: PostgreSQL + Liquibase + Airflow + Keycloak to manage database schema, jobs, and access

## What the app does

Think of MetaConnect as a control panel for data catalog metadata.

- A user logs in through Keycloak
- They create a connection to a data source
- The backend stores the source definition and encrypted credentials
- A connector reads the schema details from that source
- Metadata is saved in the PostgreSQL catalog database
- Users can browse tables, columns, and related information
- Pipelines can be created to automatically collect metadata on a schedule or manually
- Airflow runs those ingestion jobs in the background

## Main tech stack

- Frontend: React + Vite
- Backend: FastAPI + SQLAlchemy + PostgreSQL
- Authentication: Keycloak
- Workflow orchestration: Apache Airflow
- Schema migration: Liquibase
- Sample data connectors: Snowflake, Pinot

## Project folder structure

```text
MetaConnect/
│ 
├── airflow/                      # Airflow setup, dags, plugins, and dependencies
│   ├── Dockerfile
│   ├── dags/
│   ├── services/
│   └── requirements.txt
│ 
├── backend/                      # FastAPI backend and database schema files
│   ├── app/
│   │   ├── connectors/           # source-specific metadata connectors (Snowflake, Pinot)
│   │   ├── core/                # auth, config, encryption helpers
│   │   ├── database/            # SQLAlchemy models and DB setup
│   │   ├── integrations/        # integrations-related logic
│   │   ├── routes/              # API routes for services, metadata, connections, etc
│   │   ├── schemas/             # request/response schemas
│   │   └── services/            # business logic for catalog and connection workflows
│   ├── liquibase/               # database migration changelogs
│   ├── Dockerfile
│   ├── main.py                  # FastAPI app entry point
│   └── requirements.txt
│ 
├── frontend/                     # React frontend application
│   ├── public/
│   ├── src/
│   │   ├── assets/              # logos and images
│   │   ├── components/          # reusable UI widgets
│   │   ├── config/              # connector definitions
│   │   ├── layouts/             # app layout and route structure
│   │   ├── pages/               # pages such as Dashboard, Connections, Metadata Explorer
│   │   ├── services/            # frontend API/auth services
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── main.jsx
│   │   └── index.css
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   └── vite.config.*
│ 
├── keycloak/                     # Keycloak realm setup and Docker config
│   ├── Dockerfile
│   └── realm-export.json
│ 
├── .env                          # environment configuration for PostgreSQL, Airflow, ├── Keycloak
├── docker-compose.yaml           # main Docker setup for all services
├── README.md                     # project overview and setup guide
└── .gitignore

```

## Main backend areas

The backend is organized around clear responsibilities:

- `backend/app/routes/`
  - API entry points for services, connections, metadata, catalog, and pipelines
- `backend/app/services/`
  - service-level logic handling data source operations and pipeline workflows
- `backend/app/connectors/`
  - connector classes for Snowflake and Pinot metadata extraction
- `backend/app/database/`
  - SQLAlchemy models for services, databases, schemas, tables, columns, and ingestion runs
- `backend/app/core/`
  - authentication, configuration, and encryption helpers

## Main frontend areas

The frontend is organized around end-user workflows:

- `Dashboard` shows system overview and key actions
- `Connections` manages configured connections
- `AvailableConnections` lists supported connectors
- `ConnectorConnection` creates a new source connection
- `MetadataExplorer` lets users inspect metadata structures
- `PipelineRuns` tracks pipeline execution history
- `CreatePipeline` sets up metadata ingestion jobs

## How to run the project

### 1. Install Docker and Docker Compose

Make sure Docker is installed and running on your machine.

### 2. Start the project

From the project root, run:

```bash
docker compose up -d --build
```

This will start the following services:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs
- Airflow UI: http://localhost:8080
- Keycloak: http://localhost:8180
- PostgreSQL: localhost:5433

### 3. Stop the project

```bash
docker compose down
```

To remove database volumes too:

```bash
docker compose down -v
```

## Notes

- Backend APIs are organized by domain and are exposed under `/api/...`
- Metadata is stored in PostgreSQL using SQLAlchemy models
- Liquibase handles database schema changes over time
- Airflow orchestrates pipeline execution jobs
- Keycloak secures user access in the app
- Secrets and environment values are loaded from the `.env` file

## Typical user flow

A common flow in MetaConnect looks like this:

1. Log in
2. Open Connections
3. Choose a connector type such as Snowflake or Pinot
4. Add connection details
5. Save the connection
6. Create or run a pipeline for metadata ingestion
7. Monitor execution in pipeline logs and Airflow
8. Inspect catalogs, schemas, tables, and columns

## Summary

MetaConnect is a practical metadata catalog and ingestion platform. It helps teams connect to their data sources, understand what is inside them, and automate the collection of metadata in a clean and organized way.

