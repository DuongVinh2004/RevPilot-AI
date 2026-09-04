# RevPilot AI — Staging Infrastructure Outputs
# Conforms to docs/30-deployment/DEPLOYMENT-ARCHITECTURE.md

output "vpc_id" {
  description = "VPC identifier"
  value       = aws_vpc.main.id
}

output "dmz_subnet_ids" {
  description = "Zone 1 DMZ Ingress Subnet IDs"
  value       = aws_subnet.public_dmz[*].id
}

output "compute_subnet_ids" {
  description = "Zone 2 Private Compute Subnet IDs"
  value       = aws_subnet.private_compute[*].id
}

output "persistence_subnet_ids" {
  description = "Zone 3 Isolated Persistence Subnet IDs"
  value       = aws_subnet.isolated_persistence[*].id
}

output "alb_dns_name" {
  description = "DNS name of the public Application Load Balancer"
  value       = aws_lb.api.dns_name
}

output "ecs_cluster_name" {
  description = "Name of ECS Cluster"
  value       = aws_ecs_cluster.main.name
}

output "rds_cluster_endpoint" {
  description = "Aurora PostgreSQL cluster endpoint"
  value       = aws_rds_cluster.aurora.endpoint
}

output "kms_key_arn" {
  description = "Customer Managed KMS Key ARN"
  value       = aws_kms_key.main.arn
}

output "secrets_manager_arn" {
  description = "Secrets Manager Store ARN"
  value       = aws_secretsmanager_secret.platform_config.arn
}
