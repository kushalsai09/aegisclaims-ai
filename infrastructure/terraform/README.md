# Phase 7 AWS Terraform foundation

This directory describes the approved production topology. It has not been
applied to an AWS account. Runtime secret values are created and rotated
outside Terraform and supplied through the `runtime_secret_arn` variable.
The reference uses ECS/Fargate behind an ALB, RDS PostgreSQL Multi-AZ,
ElastiCache Valkey, private/versioned S3, immutable ECR, Secrets Manager
references, private endpoints, autoscaling, CloudWatch logs/alarms, and a
required private OTLP collector endpoint.

```bash
terraform fmt -check -recursive infrastructure/terraform
terraform -chdir=infrastructure/terraform init -backend=false
terraform -chdir=infrastructure/terraform validate
```

Copy `terraform.tfvars.example` to a private, ignored tfvars file before a
real plan. Remote state, locking, account selection, certificate, DNS, image
digests, and approved runtime secret values are deployment prerequisites.

Architecture behavior follows AWS documentation for [ECS service load
balancing](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-load-balancing.html),
[ECS Secrets Manager references](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/secrets-envvar-secrets-manager.html),
[RDS-managed master credentials](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-secrets-manager.html),
and [S3 versioning as a recovery control](https://docs.aws.amazon.com/AmazonS3/latest/userguide/backup-for-s3.html).
