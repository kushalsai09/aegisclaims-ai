variable "name" {
  type    = string
  default = "insurance-operations"
}
variable "environment" {
  type = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be staging or production"
  }
}
variable "aws_region" { type = string }
variable "vpc_cidr" {
  type    = string
  default = "10.42.0.0/16"
}
variable "certificate_arn" { type = string }
variable "host_name" { type = string }
variable "route53_zone_id" {
  type     = string
  default  = null
  nullable = true
}
variable "api_image" { type = string }
variable "worker_image" { type = string }
variable "web_image" { type = string }
variable "runtime_secret_arn" { type = string }
variable "oidc_issuer" { type = string }
variable "oidc_audience" { type = string }
variable "oidc_client_id" { type = string }
variable "oidc_tenant_id" { type = string }
variable "bedrock_model_id" { type = string }
variable "otel_exporter_otlp_endpoint" {
  type        = string
  description = "Private OTLP/HTTP collector endpoint reachable from ECS tasks"
}
variable "alarm_action_arns" {
  type        = list(string)
  default     = []
  description = "SNS or incident-management actions for production alarms"
}
variable "postgres_engine_version" {
  type     = string
  default  = null
  nullable = true
}
variable "db_instance_class" {
  type    = string
  default = "db.r7g.large"
}
variable "cache_node_type" {
  type    = string
  default = "cache.r7g.large"
}
variable "deletion_protection" {
  type    = bool
  default = true
}
