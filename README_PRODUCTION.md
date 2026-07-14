# SPIP Production Deployment Guide

This guide explains how to deploy SPIP to the production environment.

## Prerequisites

- Docker and Docker Compose
- Production environment variables configured in `.env.production`
- Cloud Services configured (PostgreSQL, Redis, Qdrant, Brevo, Gemini)

## Configuration

The production environment uses `.env.production`. Do NOT use default passwords or localhost references. Ensure `ENVIRONMENT=production` is set.

## Deployment

To start the production environment using Docker:

```bash
ENVIRONMENT=production docker-compose -f docker-compose.yml up -d --build
```
