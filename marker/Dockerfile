FROM python:3.9-slim

# Set non-interactive mode for apt-get
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install required system packages
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    tesseract-ocr \
    tesseract-ocr-heb \
    tesseract-ocr-eng \
    libtesseract-dev \
    poppler-utils \
    libmagic1 \
    libffi-dev \
    libjpeg-dev \
    libxml2-dev \
    libxslt-dev \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Create folder for files
RUN mkdir -p /pd

# Copy project files
COPY . /app/

# Upgrade pip and related tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install marker-pdf with extras (fixing the issue by quoting the package spec)
RUN pip install --no-cache-dir --upgrade "marker-pdf[full]==0.2.7"

# Install remaining dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Fix marker.converters issue by creating the necessary symbolic link
RUN mkdir -p /usr/local/lib/python3.9/site-packages/marker \
    && touch /usr/local/lib/python3.9/site-packages/marker/__init__.py \
    && ln -sf /usr/local/lib/python3.9/site-packages/marker_pdf/converters /usr/local/lib/python3.9/site-packages/marker/

# Optional: Verify installation of marker and its files
RUN pip list | grep marker \
    && ls -la /usr/local/lib/python3.9/site-packages/marker*

# Set PYTHONPATH for the application
ENV PYTHONPATH="/app:/usr/local/lib/python3.9/site-packages"

# Expose the port for the service
EXPOSE 8000

# Set write permissions for /pd
RUN chmod -R 777 /pd

# Run the service using uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
