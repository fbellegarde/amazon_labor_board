# Define the required providers and their versions.
# This ensures Terraform can interact with Docker.
terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

# Configure the Docker provider to connect to your local Docker daemon on Windows.
provider "docker" {
  host = "npipe:////./pipe/docker_engine"
}

# Define the Docker image resource.
# This tells Terraform to manage the 'labor-board:latest' image.
# The `keep_locally = true` argument ensures the image isn't deleted when the container is destroyed.
resource "docker_image" "labor_board_image" {
  name = "labor-board:latest"
  keep_locally = true
}

# Define the Docker container resource.
# This tells Terraform to create and manage a container named 'labor_board_container'.
resource "docker_container" "labor_board_container" {
  name  = "labor_board_container"
  image = docker_image.labor_board_image.name
  ports {
    internal = 8000
    external = 8000
    ip = "172.27.96.1" # Add this line
  }
}