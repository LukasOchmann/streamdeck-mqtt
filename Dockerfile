FROM python:3.9-alpine

# Install dependencies including Rust
RUN apk add --no-cache \
    build-base cairo-dev cairo cairo-tools \
    jpeg-dev zlib-dev freetype-dev lcms2-dev openjpeg-dev tiff-dev tk-dev tcl-dev hidapi-dev \
    rust cargo

# Set working directory
WORKDIR /app

# Copy application files
COPY ./src ./src
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Set default command
CMD ["python", "src/main.py"]
