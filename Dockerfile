# Use an official Python runtime as the base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    virtualenv \
    && rm -rf /var/lib/apt/lists/*

# Copy the bin scripts
COPY bin/ ./bin/

# Make sure the scripts are executable
RUN chmod +x ./bin/*

# Copy the requirements file into the container
COPY requirements.in .

# Install the Python dependencies
RUN /app/bin/install.sh

# Copy the application code
COPY app/ ./app/

# Copy the alembic artifacts
COPY alembic/ ./alembic/
COPY alembic.ini ./alembic.ini

# Copy the static assets
COPY static/ ./static/

# Copy the html templates
COPY templates/ ./templates/

# Create a startup script
RUN echo '#!/bin/bash' > /app/start.sh && \
    echo '/app/bin/migrate.sh' >> /app/start.sh && \
    echo '/app/bin/run.sh' >> /app/start.sh && \
    chmod +x /app/start.sh

# Expose the port the app runs on
EXPOSE 8000

# Set the entrypoint to our startup script
ENTRYPOINT ["/app/start.sh"]
