# Use a slim version of Python
FROM python:3.11-slim

# Install cron
RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install (if you have a requirements.txt)
# For now, we'll install directly to keep it simple
RUN pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib

# Copy the script and credentials
# IMPORTANT: token.json must be present so the container doesn't try 
# to open a browser for OAuth (which it can't do)
COPY main.py .
COPY credentials.json .
COPY token.json .
COPY crontab /etc/cron.d/daily-cron

# Give execution rights and apply the cron job
RUN chmod 0644 /etc/cron.d/daily-cron && \
    crontab /etc/cron.d/daily-cron && \
    touch /var/log/cron.log

# Run cron in the foreground
CMD ["cron", "-f"]