FROM python:3.9-alpine

# Install dependencies
RUN apk add --no-cache \
    build-base cairo-dev cairo cairo-tools \
    jpeg-dev zlib-dev freetype-dev lcms2-dev openjpeg-dev tiff-dev tk-dev tcl-dev hidapi-dev

# Set up working directory
WORKDIR /app

# Copy app files
COPY ./src ./src
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Run the app
CMD ["python", "src/main.py"]
