resource "aws_ecs_cluster" "main" {
  name = "${var.name}-${var.environment}"
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}
resource "aws_cloudwatch_log_group" "service" {
  for_each          = toset(["api", "worker", "web"])
  name              = "/ecs/${var.name}/${var.environment}/${each.value}"
  retention_in_days = 30
}

locals {
  common_environment = [
    { name = "APP_ENV", value = var.environment },
    { name = "AUTH_PROVIDER", value = "oidc" },
    { name = "OIDC_ISSUER", value = var.oidc_issuer },
    { name = "OIDC_AUDIENCE", value = var.oidc_audience },
    { name = "OIDC_CLIENT_ID", value = var.oidc_client_id },
    { name = "OIDC_REDIRECT_URI", value = "https://${var.host_name}/api/v1/auth/oidc/callback" },
    { name = "OIDC_TENANT_ID", value = var.oidc_tenant_id },
    { name = "PUBLIC_BASE_URL", value = "https://${var.host_name}" },
    { name = "API_CORS_ORIGINS", value = "https://${var.host_name}" },
    { name = "TRUSTED_HOSTS", value = var.host_name },
    { name = "API_DOCS_ENABLED", value = "false" },
    { name = "OBJECT_STORAGE_PROVIDER", value = "aws_s3" },
    { name = "OBJECT_STORAGE_BUCKET", value = aws_s3_bucket.documents.id },
    { name = "OBJECT_STORAGE_REGION", value = var.aws_region },
    { name = "QUEUE_PROVIDER", value = "redis" },
    { name = "RATE_LIMIT_PROVIDER", value = "redis" },
    { name = "MODEL_PROVIDER", value = "bedrock" },
    { name = "BEDROCK_MODEL_ID", value = var.bedrock_model_id },
    { name = "BEDROCK_REGION", value = var.aws_region },
    { name = "OTEL_ENABLED", value = "true" },
    { name = "OTEL_EXPORTER_OTLP_ENDPOINT", value = var.otel_exporter_otlp_endpoint }
  ]
  runtime_secrets = [
    { name = "DATABASE_URL", valueFrom = "${var.runtime_secret_arn}:DATABASE_URL::" },
    { name = "REDIS_URL", valueFrom = "${var.runtime_secret_arn}:REDIS_URL::" },
    { name = "OIDC_CLIENT_SECRET", valueFrom = "${var.runtime_secret_arn}:OIDC_CLIENT_SECRET::" }
  ]
  log_options = {
    api = {
      awslogs-group         = aws_cloudwatch_log_group.service["api"].name
      awslogs-region        = var.aws_region
      awslogs-stream-prefix = "api"
    }
    worker = {
      awslogs-group         = aws_cloudwatch_log_group.service["worker"].name
      awslogs-region        = var.aws_region
      awslogs-stream-prefix = "worker"
    }
    web = {
      awslogs-group         = aws_cloudwatch_log_group.service["web"].name
      awslogs-region        = var.aws_region
      awslogs-stream-prefix = "web"
    }
  }
}

resource "aws_ecs_task_definition" "api" {
  family                   = "${var.name}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 1024
  memory                   = 2048
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.application.arn
  container_definitions = jsonencode([{
    name                   = "api"
    image                  = var.api_image
    essential              = true
    readonlyRootFilesystem = true
    linuxParameters = {
      initProcessEnabled = true
      tmpfs = [{
        containerPath = "/tmp"
        size          = 64
        mountOptions  = ["rw", "noexec", "nosuid", "nodev"]
      }]
    }
    portMappings     = [{ containerPort = 8000, protocol = "tcp" }]
    environment      = local.common_environment
    secrets          = local.runtime_secrets
    logConfiguration = { logDriver = "awslogs", options = local.log_options.api }
    healthCheck = {
      command     = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live')\""]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 30
    }
  }])
}
resource "aws_ecs_task_definition" "worker" {
  family                   = "${var.name}-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.application.arn
  container_definitions = jsonencode([{
    name                   = "worker"
    image                  = var.worker_image
    essential              = true
    readonlyRootFilesystem = true
    linuxParameters = {
      initProcessEnabled = true
      tmpfs = [{
        containerPath = "/tmp"
        size          = 64
        mountOptions  = ["rw", "noexec", "nosuid", "nodev"]
      }]
    }
    environment      = local.common_environment
    secrets          = local.runtime_secrets
    logConfiguration = { logDriver = "awslogs", options = local.log_options.worker }
  }])
}
resource "aws_ecs_task_definition" "web" {
  family                   = "${var.name}-web"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.execution.arn
  container_definitions = jsonencode([{
    name                   = "web"
    image                  = var.web_image
    essential              = true
    readonlyRootFilesystem = true
    linuxParameters = {
      initProcessEnabled = true
      tmpfs = [
        {
          containerPath = "/tmp"
          size          = 32
          mountOptions  = ["rw", "noexec", "nosuid", "nodev"]
        },
        {
          containerPath = "/var/cache/nginx"
          size          = 64
          mountOptions  = ["rw", "noexec", "nosuid", "nodev"]
        },
        {
          containerPath = "/var/run"
          size          = 8
          mountOptions  = ["rw", "noexec", "nosuid", "nodev"]
        }
      ]
    }
    portMappings     = [{ containerPort = 8080, protocol = "tcp" }]
    logConfiguration = { logDriver = "awslogs", options = local.log_options.web }
    healthCheck = {
      command     = ["CMD-SHELL", "wget -q -O /dev/null http://127.0.0.1:8080/healthz"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 10
    }
  }])
}

resource "aws_lb" "main" {
  name_prefix                = "ins-"
  internal                   = false
  load_balancer_type         = "application"
  security_groups            = [aws_security_group.alb.id]
  subnets                    = values(aws_subnet.public)[*].id
  drop_invalid_header_fields = true
}
resource "aws_lb_target_group" "api" {
  name_prefix = "api-"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"
  health_check {
    path    = "/health/ready"
    matcher = "200"
  }
}
resource "aws_lb_target_group" "web" {
  name_prefix = "web-"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"
  health_check {
    path    = "/healthz"
    matcher = "200"
  }
}
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web.arn
  }
}
resource "aws_lb_listener_rule" "api" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 10
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
  condition {
    path_pattern {
      values = ["/api/*", "/health/*"]
    }
  }
}

resource "aws_ecs_service" "api" {
  name                              = "api"
  cluster                           = aws_ecs_cluster.main.id
  task_definition                   = aws_ecs_task_definition.api.arn
  desired_count                     = 2
  launch_type                       = "FARGATE"
  health_check_grace_period_seconds = 60
  network_configuration {
    subnets          = values(aws_subnet.private)[*].id
    security_groups  = [aws_security_group.tasks.id]
    assign_public_ip = false
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
}
resource "aws_ecs_service" "web" {
  name                              = "web"
  cluster                           = aws_ecs_cluster.main.id
  task_definition                   = aws_ecs_task_definition.web.arn
  desired_count                     = 2
  launch_type                       = "FARGATE"
  health_check_grace_period_seconds = 30
  network_configuration {
    subnets          = values(aws_subnet.private)[*].id
    security_groups  = [aws_security_group.tasks.id]
    assign_public_ip = false
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.web.arn
    container_name   = "web"
    container_port   = 8080
  }
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
}
resource "aws_ecs_service" "worker" {
  name            = "worker"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = 2
  launch_type     = "FARGATE"
  network_configuration {
    subnets          = values(aws_subnet.private)[*].id
    security_groups  = [aws_security_group.tasks.id]
    assign_public_ip = false
  }
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
}

resource "aws_route53_record" "app" {
  count   = var.route53_zone_id == null ? 0 : 1
  zone_id = var.route53_zone_id
  name    = var.host_name
  type    = "A"
  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}
