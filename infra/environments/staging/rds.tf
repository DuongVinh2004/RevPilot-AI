# RevPilot AI — Managed Relational Database (Aurora PostgreSQL)
# Conforms to DEC-004, ADR-0004, ADR-0005, and INV-REL-001

resource "aws_db_subnet_group" "rds" {
  name        = "revpilot-${var.environment}-db-subnet-group"
  description = "Isolated database subnet group across 3 AZs"
  subnet_ids  = aws_subnet.isolated_persistence[*].id

  tags = {
    Name = "revpilot-${var.environment}-db-subnet-group"
    Zone = "Zone-3-Isolated-Persistence"
  }
}

resource "aws_rds_cluster_parameter_group" "pg16" {
  name        = "revpilot-${var.environment}-pg16-params"
  family      = "aurora-postgresql16"
  description = "Parameter group enforcing TLS transport encryption and logging"

  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }

  parameter {
    name  = "log_connections"
    value = "1"
  }

  parameter {
    name  = "log_disconnections"
    value = "1"
  }
}

resource "aws_rds_cluster" "aurora" {
  cluster_identifier              = "revpilot-${var.environment}-aurora"
  engine                          = "aurora-postgresql"
  engine_version                  = "16.1"
  database_name                   = "revpilot_db"
  master_username                 = "revpilot_admin"
  manage_master_user_password     = true
  master_user_secret_kms_key_id   = aws_kms_key.main.key_id
  db_subnet_group_name            = aws_db_subnet_group.rds.name
  vpc_security_group_ids          = [aws_security_group.rds.id]
  db_cluster_parameter_group_name = aws_rds_cluster_parameter_group.pg16.name

  # Security & Compliance Invariants
  storage_encrypted   = true
  kms_key_id          = aws_kms_key.main.arn
  deletion_protection = true

  # High Availability & Backup Retentions (DEC-011: RPO <= 5m)
  backup_retention_period = 7
  preferred_backup_window = "02:00-03:00"

  serverlessv2_scaling_configuration {
    min_capacity = var.aurora_min_capacity
    max_capacity = var.aurora_max_capacity
  }

  tags = {
    Name = "revpilot-${var.environment}-aurora-cluster"
    Zone = "Zone-3-Isolated-Persistence"
  }
}

resource "aws_rds_cluster_instance" "aurora_instances" {
  count               = 2 # Multi-AZ High Availability
  identifier          = "revpilot-${var.environment}-aurora-inst-${count.index + 1}"
  cluster_identifier  = aws_rds_cluster.aurora.id
  instance_class      = "db.serverless"
  engine              = aws_rds_cluster.aurora.engine
  engine_version      = aws_rds_cluster.aurora.engine_version
  publicly_accessible = false

  tags = {
    Name = "revpilot-${var.environment}-aurora-inst-${count.index + 1}"
    Zone = "Zone-3-Isolated-Persistence"
  }
}
