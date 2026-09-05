output "load_balancer_dns_name" { value = aws_lb.main.dns_name }
output "document_bucket_name" { value = aws_s3_bucket.documents.id }
output "database_endpoint" {
  value     = aws_db_instance.postgres.endpoint
  sensitive = true
}
output "cache_primary_endpoint" {
  value     = aws_elasticache_replication_group.cache.primary_endpoint_address
  sensitive = true
}
output "ecs_cluster_name" { value = aws_ecs_cluster.main.name }
