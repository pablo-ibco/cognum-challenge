# Use an official Python runtime as the base image
FROM python:3.9

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file to the working directory
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Chromium and necessary packages
RUN apt-get update && apt-get install -y wget unzip xvfb
RUN apt-get install -y chromium chromium-driver

# Copy the application code to the working directory
COPY . .

ARG SCRIPT_NAME

# Run the app
CMD ["python", "-u", "${SCRIPT_NAME}"]
