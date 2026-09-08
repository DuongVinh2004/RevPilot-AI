# RevPilot AI — ECS Fargate Cluster and Services Topology
# Conforms to docs/30-deployment/DEPLOYMENT-ARCHITECTURE.md §6 and DEC-004

resource "aws_ecs_cluster" "main" {
  name = "revpilot-${var.environment}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name = "revpilot-${var.environment}-ecs-cluster"
  }
}

# --- CloudWatch Logging Group ---
resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/revpilot-${var.environment}"
  retention_in_days = 30
  kms_key_id        = aws_kms_key.main.arn

  tags = {
    Name = "revpilot-${var.environment}-ecs-logs"
  }
}

# --- IAM Roles for ECS Execution & Task ---
resource "aws_iam_role" "ecs_execution" {
  name = "revpilot-${var.environment}-ecs-execution-role"

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

resource "aws_iam_role_policy_attachment" "ecs_execution_base" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ecs_task" {
  name = "revpilot-${var.environment}-ecs-task-role"

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

# --- 1. Service: revpilot-api ---
resource "aws_ecs_task_definition" "api" {
  family                   = "revpilot-${var.environment}-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "api"
      image     = var.api_container_image
      essential = true
      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
          protocol      = "tcp"
        }
      ]
      environment = [
        { name = "PORT", value = "8000" },
        { name = "LOG_LEVEL", value = "INFO" }
      ]
      secrets = [
        {
          name      = "DATABASE_URL"
          valueFrom = "${aws_secretsmanager_secret.platform_config.arn}:DATABASE_URL::"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "api"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "api" {
  name            = "revpilot-${var.environment}-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private_compute[*].id
    security_groups  = [aws_security_group.ecs_api.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener.https]
}

# --- 2. Service: revpilot-workflow-worker ---
resource "aws_ecs_task_definition" "workflow_worker" {
  family                   = "revpilot-${var.environment}-workflow-worker"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "2048"
  memory                   = "4096"
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "workflow-worker"
      image     = var.workflow_worker_image
      essential = true
      environment = [
        { name = "LOG_LEVEL", value = "INFO" }
      ]
      secrets = [
        {
          name      = "DATABASE_URL"
          valueFrom = "${aws_secretsmanager_secret.platform_config.arn}:DATABASE_URL::"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "workflow-worker"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "workflow_worker" {
  name            = "revpilot-${var.environment}-workflow-worker"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.workflow_worker.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private_compute[*].id
    security_groups  = [aws_security_group.ecs_workers.id]
    assign_public_ip = false
  }
}

# --- 3. Service: revpilot-ml-worker ---
resource "aws_ecs_task_definition" "ml_worker" {
  family                   = "revpilot-${var.environment}-ml-worker"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "2048"
  memory                   = "8192"
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "ml-worker"
      image     = var.ml_worker_image
      essential = true
      environment = [
        { name = "LOG_LEVEL", value = "INFO" },
        { name = "ZERO_DATA_RETENTION", value = "true" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ml-worker"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "ml_worker" {
  name            = "revpilot-${var.environment}-ml-worker"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.ml_worker.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private_compute[*].id
    security_groups  = [aws_security_group.ecs_workers.id]
    assign_public_ip = false
  }
}

# --- 4. Service: revpilot-ingestion-worker ---
resource "aws_ecs_task_definition" "ingestion_worker" {
  family                   = "revpilot-${var.environment}-ingestion-worker"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "4096"
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "ingestion-worker"
      image     = var.ingestion_worker_image
      essential = true
      environment = [
        { name = "LOG_LEVEL", value = "INFO" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ingestion-worker"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "ingestion_worker" {
  name            = "revpilot-${var.environment}-ingestion-worker"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.ingestion_worker.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private_compute[*].id
    security_groups  = [aws_security_group.ecs_workers.id]
    assign_public_ip = false
  }
}
