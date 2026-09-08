# RevPilot AI — Security Groups and Network Boundary Controls
# Conforms to docs/30-deployment/DEPLOYMENT-ARCHITECTURE.md §5 and AC-DEP-01

# --- Zone 1: ALB Security Group ---
resource "aws_security_group" "alb" {
  name        = "revpilot-${var.environment}-alb-sg"
  description = "Controls inbound HTTPS traffic to API Gateway ALB"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTPS ingress from restricted internal CIDR"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    description     = "Forward traffic to ECS API tasks"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_api.id]
  }

  tags = {
    Name = "revpilot-${var.environment}-alb-sg"
    Zone = "Zone-1-DMZ-Ingress"
  }
}

# --- Zone 2: ECS API Tasks Security Group ---
resource "aws_security_group" "ecs_api" {
  name        = "revpilot-${var.environment}-ecs-api-sg"
  description = "Controls ingress and egress for revpilot-api ECS tasks"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Allow HTTP ingress from ALB only"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = []
  }

  egress {
    description = "Outbound HTTPS for AWS APIs and internal endpoints"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = {
    Name = "revpilot-${var.environment}-ecs-api-sg"
    Zone = "Zone-2-Private-Compute"
  }
}

resource "aws_security_group_rule" "alb_to_api" {
  type                     = "ingress"
  from_port                = 8000
  to_port                  = 8000
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.alb.id
  security_group_id        = aws_security_group.ecs_api.id
}

# --- Zone 2: ECS Workers Security Group ---
resource "aws_security_group" "ecs_workers" {
  name        = "revpilot-${var.environment}-ecs-workers-sg"
  description = "Controls egress for background worker tasks (no public ingress)"
  vpc_id      = aws_vpc.main.id

  egress {
    description = "Outbound HTTPS for internal routing and AWS APIs"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = {
    Name = "revpilot-${var.environment}-ecs-workers-sg"
    Zone = "Zone-2-Private-Compute"
  }
}

# --- Zone 3: RDS Aurora Persistence Security Group ---
resource "aws_security_group" "rds" {
  name        = "revpilot-${var.environment}-rds-sg"
  description = "Controls access to PostgreSQL database (compute tier only)"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "PostgreSQL from API tasks and workers"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_api.id, aws_security_group.ecs_workers.id]
  }

  tags = {
    Name = "revpilot-${var.environment}-rds-sg"
    Zone = "Zone-3-Isolated-Persistence"
  }
}
