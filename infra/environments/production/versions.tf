# RevPilot AI — Production Infrastructure Terraform Requirements
# Conforms to docs/30-deployment/DEPLOYMENT-ARCHITECTURE.md and DEC-004

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.30.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "RevPilot-AI"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Owner       = "SRE-Lead"
    }
  }
}
