# D:\amazon_labor_board\Dockerfile

# Use an official Python runtime as a parent image
FROM python:3.12-slim-bullseye

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variable for running in production
ENV UVICORN_HOST=0.0.0.0

# Run the uvicorn server with the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]