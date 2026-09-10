# Start from a ready-made image: Debian with Python 3.13, "slim" = no extras.
FROM python:3.13-slim

# Everything below happens inside /app in the image. Created if missing.
WORKDIR /app

# Put the five scripts on the shelf at /app. Nothing runs yet.
# data/ is deliberately NOT copied: it is mounted at run time.
COPY refresh.py validate.py build_page.py manage.py movers.py movers_image.py test_validate.py test_movers.py ./

# The start script: catch-up refresh on every container start, then cron.
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh
# Run the unit tests while building. A failing test aborts the build,
# so a broken image can never exist.
RUN python -m unittest test_validate test_movers -v

# Install cron, the Linux scheduler, and the DejaVu font for the movers PNG. The slim image has neither.
# rm -rf afterwards deletes the package index to keep the image small.
RUN apt-get update && apt-get install -y --no-install-recommends cron fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
# Pillow draws the movers PNG. Pinned so a rebuild months later gets the same library.
RUN pip install --no-cache-dir pillow==12.3.0

# Write one schedule line and load it into cron.
#   0 6 * * *   = minute 0, hour 6, every day
#   cd /app/data && python /app/refresh.py   = the job
#   >> /proc/1/fd/1 2>&1   = send its output to the container log (docker logs)
RUN echo '0 6 * * * cd /app/data && python /app/refresh.py >> /proc/1/fd/1 2>&1' > /etc/cron.d/ledger \
    && chmod 0644 /etc/cron.d/ledger \
    && crontab /etc/cron.d/ledger

# Default command when the container starts with no command given:
# cron in the foreground (-f). A container lives as long as its main process,
# so this keeps it running and firing the schedule.
# Default command: start.sh runs one refresh, then hands over to cron -f.
CMD ["/app/start.sh"]
