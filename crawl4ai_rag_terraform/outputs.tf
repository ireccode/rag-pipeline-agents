output "api_gateway_invoke_url" {
  description = "The base URL for the API Gateway invocation"
  value       = aws_apigatewayv2_api.lambda_api.api_endpoint
}

output "lambda_arn" {
  description = "The ARN of the deployed Lambda function"
  value       = aws_lambda_function.crawl4ai.arn
}

output "ecr_repository_uri" {
  description = "The URI of the ECR repository"
  value       = aws_ecr_repository.crawl4ai_mcp.repository_url
}

output "neo4j_ec2_private_ip" {
  description = "The private IP address of the Neo4j EC2 instance"
  value       = aws_instance.neo4j.private_ip
}

output "neo4j_ec2_public_ip" {
  description = "The public IP address of the Neo4j EC2 instance"
  value       = aws_instance.neo4j.public_ip
}

output "curl_test_command" {
  description = "Example curl command for testing the API Gateway endpoint"
  value = "curl -X POST ${aws_apigatewayv2_api.lambda_api.api_endpoint}/crawl4ai -d '{\"command\":\"query_knowledge_graph\"}'"
}


output "aurora_cluster_endpoint" {
  description = "The cluster endpoint for the Aurora PostgreSQL database"
  value       = aws_rds_cluster.crawl4ai_db.endpoint
}

output "aurora_database_url" {
  description = "The full DATABASE_URL for the application"
  value       = aws_lambda_function.crawl4ai.environment[0].variables.DATABASE_URL
  sensitive   = true
}
