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

# List files for debugging
RUN echo "הקבצים שהועתקו לתיקיית /app:" && \
    ls -la /app && \
    echo "הקבצים שהועתקו לתיקיית /app/app:" && \
    ls -la /app/app || echo "תיקיית app לא קיימת"

# Upgrade pip and related tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Create pip.conf with higher timeout settings
RUN mkdir -p /root/.config/pip && \
    echo "[global]\ntimeout = 100\nretries = 5" > /root/.config/pip/pip.conf

# Install marker-pdf with multiple retry attempts
RUN for i in $(seq 1 3); do \
    echo "Trial $i: Installing marker-pdf..." && \
    pip install --no-cache-dir --upgrade "marker-pdf[full]==0.2.7" && break || \
    echo "Attempt $i failed! Waiting 10 seconds..." && \
    sleep 10; \
    done

# Install remaining dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Fix marker.converters issue by creating the necessary symbolic link
RUN mkdir -p /usr/local/lib/python3.9/site-packages/marker \
    && touch /usr/local/lib/python3.9/site-packages/marker/__init__.py \
    && ln -sf /usr/local/lib/python3.9/site-packages/marker_pdf/converters /usr/local/lib/python3.9/site-packages/marker/

# Verify installation of marker and its files
RUN pip list | grep marker \
    && ls -la /usr/local/lib/python3.9/site-packages/marker*

# Make sure the __init__.py files exist in app directories
RUN touch /app/app/__init__.py \
    && touch /app/app/routes/__init__.py \
    && touch /app/app/services/__init__.py

# Set PYTHONPATH for the application
ENV PYTHONPATH="/app"

# Expose the port for the service
EXPOSE 8000

# Set write permissions for /pd
RUN chmod -R 777 /pd

# Run debug check when starting the container
CMD echo "בדיקת קבצים עם דיבוג:" && \
    echo "תיקיית נוכחית:" && pwd && \
    echo "תוכן התיקייה:" && ls -la && \
    echo "תוכן תיקיית app:" && ls -la app && \
    echo "בדיקת import עם Python:" && \
    python -c "import sys; print(sys.path); \
    print('Trying imports:'); \
    import app.main; print('✓ import app.main - OK'); \
    from app.main import app; print('✓ from app.main import app - OK'); \
    from app.routes import document_processing; print('✓ from app.routes import document_processing - OK');" || \
    echo "✗ שגיאות ייבוא - בדוק את הלוגים" && \
    echo "הפעלת Uvicorn:" && \
    uvicorn app.main:app --host 0.0.0.0 --port 8000
