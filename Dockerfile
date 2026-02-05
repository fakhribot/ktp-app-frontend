FROM python:3.9-slim

WORKDIR /app

# 1. Install System Dependencies & Debug Tools
# - libpq-dev, gcc: Required for your app (psycopg2)
# - procps: Adds 'ps' and 'top' (critical for checking if processes are hung)
# - iputils-ping: To ping your database or backend API
# - curl: To test HTTP endpoints from the command line
# - vim: To edit config files inside the container
# - net-tools: Adds 'netstat' to check open ports
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    procps \
    iputils-ping \
    net-tools \
    curl \
    vim \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# 2. Install Python Dependencies & Debugger
# - debugpy: Allows VS Code to attach to the running container
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install debugpy

COPY . .

# 3. Expose App Port (80) and Debugger Port (5678)
EXPOSE 80 5678

# 4. Run Command
# STANDARD MODE (Default):
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:80", "app:app"]