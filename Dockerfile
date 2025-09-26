# D:\amazon_labor_board\Dockerfile

# Use an official Python runtime as a parent image
FROM python:3.12-slim-bullseye

# Create the working directory for your application in the container
WORKDIR /app

# Copy the app folder content into the container's /app directory
COPY ./app /app

# Install any needed packages specified in requirements.txt
# Assuming requirements.txt is in the D:\amazon_labor_board directory
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variable for running in production
ENV UVICORN_HOST=0.0.0.0

# Run the uvicorn server with the application
# Now the path is just 'main' because the content is directly in /app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]