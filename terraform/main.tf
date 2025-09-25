# D:\amazon_labor_board\terraform\main.tf

# Configure the AWS Provider
provider "aws" {
  region = "us-east-1" # Or your desired region
}

# -----------------------------------------------------------
# ECR Repository
# -----------------------------------------------------------
resource "aws_ecr_repository" "labor_board_repo" {
  name                 = "amazon-labor-board-repo"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

# -----------------------------------------------------------
# ECS Cluster and Fargate Services
# -----------------------------------------------------------
resource "aws_ecs_cluster" "labor_board_cluster" {
  name = "amazon-labor-board-cluster"
}

resource "aws_ecs_task_definition" "labor_board_task" {
  family                   = "labor-board-task"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn

  container_definitions = jsonencode([
    {
      name      = "labor-board-container"
      image     = "${aws_ecr_repository.labor_board_repo.repository_url}:latest"
      essential = true
      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.labor_board_log_group.name
          "awslogs-region"        = "us-east-1"
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "labor_board_service" {
  name            = "labor-board-service"
  cluster         = aws_ecs_cluster.labor_board_cluster.id
  task_definition = aws_ecs_task_definition.labor_board_task.arn
  launch_type     = "FARGATE"
  desired_count   = 1

  network_configuration {
    subnets          = [data.aws_subnet.default_a.id, data.aws_subnet.default_b.id]
    security_groups  = [aws_security_group.labor_board_sg.id]
    assign_public_ip = true
  }

  lifecycle {
    ignore_changes = [task_definition]
  }
}

# -----------------------------------------------------------
# IAM Role for ECS
# -----------------------------------------------------------
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "ecsTaskExecutionRole"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy_attachment" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# -----------------------------------------------------------
# Networking and Security
# -----------------------------------------------------------
resource "aws_security_group" "labor_board_sg" {
  name        = "labor-board-sg"
  description = "Allow inbound traffic on port 8000"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Data sources to get default VPC and subnets
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

data "aws_subnet" "default_a" {
  id = data.aws_subnets.default.ids[0]
}

data "aws_subnet" "default_b" {
  id = data.aws_subnets.default.ids[1]
}

# -----------------------------------------------------------
# CloudWatch Logs
# -----------------------------------------------------------
resource "aws_cloudwatch_log_group" "labor_board_log_group" {
  name              = "/ecs/labor-board-app"
  retention_in_days = 7
}

# Output the ECR repository URL to use in GitHub Actions
output "ecr_repository_url" {
  description = "The URL of the ECR repository"
  value       = aws_ecr_repository.labor_board_repo.repository_url
}

# Output the ECS Service name
output "ecs_service_name" {
  description = "The name of the ECS service"
  value       = aws_ecs_service.labor_board_service.name
}