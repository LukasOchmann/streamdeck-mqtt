# Build stage
FROM python:3.9-slim-bullseye AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libcairo2-dev \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7-dev \
    libtiff5-dev \
    libhidapi-dev \
    libusb-1.0-0-dev \
 && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.9-slim-bullseye

# Install both build and runtime dependencies (needed for Python packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libcairo2 \
    libcairo2-dev \
    libjpeg62-turbo \
    libjpeg-dev \
    libhidapi-hidraw0 \
    libhidapi-dev \
    libusb-1.0-0 \
    libusb-1.0-0-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7-dev \
    libtiff5-dev \
 && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r streamdeck && useradd -r -g streamdeck -m streamdeck

# Set working directory
WORKDIR /app

# Copy application files
COPY ./src ./src
COPY requirements.txt .

# Install Python dependencies as root, then switch
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Change ownership to non-root user
RUN chown -R streamdeck:streamdeck /app

# Switch to non-root user
USER streamdeck

# Set default command
CMD ["python", "src/main.py"]