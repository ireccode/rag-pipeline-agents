resource "aws_ecr_lifecycle_policy" "crawl4ai_mcp_policy" {
  repository = aws_ecr_repository.crawl4ai_mcp.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1,
        description  = "Keep last 5 images",
        selection    = {
          tagStatus   = "any",
          countType   = "imageCountMoreThan",
          countNumber = 5
        },
        action = {
          type = "expire"
        }
      }
    ]
  })
}
