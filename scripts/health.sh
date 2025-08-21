#!/usr/bin/env bash
set -e
docker compose ps
docker compose logs -n 50 content-api bot-api pin-worker poster-worker | tail -n 200 || true
