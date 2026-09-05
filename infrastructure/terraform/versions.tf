terraform {
  required_version = ">= 1.8.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.100"
    }
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Application = var.name
      Environment = var.environment
      ManagedBy   = "terraform"
      DataClass   = "synthetic-reference"
    }
  }
}
