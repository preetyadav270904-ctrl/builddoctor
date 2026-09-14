FROM python:3.11-slim

WORKDIR /workspace

# Install git so later phases can manipulate branches/commits if mounted
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# Copy repo or project files into container
COPY . /workspace

# Install requirements if present, then ensure pytest is installed
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi
RUN pip install --no-cache-dir pytest

# Default entrypoint runs pytest on whatever is present in /workspace
CMD ["pytest"]
