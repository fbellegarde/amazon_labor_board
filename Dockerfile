# Use an official Python runtime
FROM python:3.12-slim-bullseye

# Set the working directory to /code
# We use /code instead of /app to avoid confusion with your inner 'app' folder
WORKDIR /code

# Install system dependencies (needed for some pandas/excel operations)
RUN apt-get update && apt-get install -y gcc

# Copy requirements first (for Docker caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app folder into /code/app
COPY ./app /code/app

# Create the data directory inside the container so permissions are ready
RUN mkdir -p /code/data

# Expose the port you want
EXPOSE 8090

# Run uvicorn
# Note the path: app.main:app because main.py is inside the app folder
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8090"]