FROM python:3.10-slim-buster

# Install system dependencies
RUN apt-get update && apt-get install -y \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    libgtk-3-dev \
    libatlas-base-dev \
    gfortran \
    wget \
    unzip \
    build-essential \
    pkg-config

# Install Python dependencies
RUN pip install --no-cache-dir \
    click==8.1.3 \
    cmake==3.26.1 \
    dlib==19.18.0 \
    face-recognition==1.3.0 \
    face-recognition-models==0.3.0 \
    Flask==2.2.3 \
    itsdangerous==2.1.2 \
    Jinja2==3.1.2 \
    MarkupSafe==2.1.2 \
    numpy==1.24.2 \
    opencv-python==4.7.0.72 \
    paho-mqtt==1.6.1 \
    Pillow==9.5.0 \
    pygame==2.3.0 \
    websocket-client==1.5.1 \
    Werkzeug==2.2.3

# Copy the source code to the container
COPY . /app

# Set the working directory
WORKDIR /app

# Expose the default Flask port
EXPOSE 5001

# Start the Flask application with if __name__ == '__main__'
CMD [ "python", "main.py" ]
