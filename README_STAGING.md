# SPIP Staging Deployment Guide

This guide explains how to deploy SPIP to the staging environment.

## Prerequisites

- Docker and Docker Compose
- Staging environment variables configured in `.env.staging`

## Configuration

The staging environment uses `.env.staging`. Ensure all necessary secrets and URLs are provided.

## Deployment

To start the staging environment using Docker:

```bash
ENVIRONMENT=staging docker-compose up -d --build
```

This will spin up all necessary containers using the staging configuration.
