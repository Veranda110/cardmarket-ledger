#!/bin/sh
cd /app/data && python /app/refresh.py
exec cron -f