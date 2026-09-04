# RevPilot AI — Staging Environment Variables
# Conforms to DEC-004 and DEPLOYMENT-ARCHITECTURE.md

variable "aws_region" {
  description = "Target AWS Region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment name"
  type        = string
  default     = "staging"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.100.0.0/16"
}

variable "availability_zones" {
  description = "List of target availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "public_subnet_cidrs" {
  description = "CIDRs for Zone 1: DMZ Ingress Subnets"
  type        = list(string)
  default     = ["10.100.1.0/24", "10.100.2.0/24", "10.100.3.0/24"]
}

variable "compute_subnet_cidrs" {
  description = "CIDRs for Zone 2: Private Compute Subnets"
  type        = list(string)
  default     = ["10.100.10.0/24", "10.100.11.0/24", "10.100.12.0/24"]
}

variable "persistence_subnet_cidrs" {
  description = "CIDRs for Zone 3: Isolated Persistence Subnets"
  type        = list(string)
  default     = ["10.100.20.0/24", "10.100.21.0/24", "10.100.22.0/24"]
}

variable "api_container_image" {
  description = "Container image URI for revpilot-api"
  type        = string
  default     = "revpilot/api:v1.0.0-rc1"
}

variable "workflow_worker_image" {
  description = "Container image URI for revpilot-workflow-worker"
  type        = string
  default     = "revpilot/workflow-worker:v1.0.0-rc1"
}

variable "ml_worker_image" {
  description = "Container image URI for revpilot-ml-worker"
  type        = string
  default     = "revpilot/ml-worker:v1.0.0-rc1"
}

variable "ingestion_worker_image" {
  description = "Container image URI for revpilot-ingestion-worker"
  type        = string
  default     = "revpilot/ingestion-worker:v1.0.0-rc1"
}

variable "aurora_min_capacity" {
  description = "Aurora Serverless v2 Min ACUs"
  type        = number
  default     = 0.5
}

variable "aurora_max_capacity" {
  description = "Aurora Serverless v2 Max ACUs"
  type        = number
  default     = 8.0
}
