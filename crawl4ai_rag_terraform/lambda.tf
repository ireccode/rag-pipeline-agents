resource "aws_lambda_function" "crawl4ai" {
  function_name = "crawl4ai_mcp"
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.crawl4ai_mcp.repository_url}@${var.image_digest}"
  role          = aws_iam_role.lambda_exec.arn
  timeout       = 900 # 15 minutes max
  memory_size   = 1024
  
  # VPC configuration to allow communication with Neo4j
  vpc_config {
    subnet_ids         = [for s in aws_subnet.private : s.id]
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  environment {
    variables = {
      # Aurora Database (replaces Supabase)
      DATABASE_URL                 = "postgresql://${var.db_username}:${var.db_master_password}@${aws_rds_cluster.crawl4ai_db.endpoint}:5432/${var.db_name}"
      
      # Neo4j Configuration
      NEO4J_URI                    = "bolt://${aws_instance.neo4j.private_ip}:7687"
      NEO4J_USER                   = "neo4j"
      NEO4J_PASSWORD               = var.neo4j_password
      
      # Core Application Configuration
      TRANSPORT                    = "sse" # Lambda is invoked by API Gateway (HTTP), so SSE is appropriate for the app logic
      HOST                         = "0.0.0.0"
      PORT                         = "8051" # Internal port, not exposed directly
      OPENAI_API_KEY               = var.openai_api_key
      MODEL_CHOICE                 = var.model_choice
      CORPUS_URL                   = var.corpus_url
      FLIGHTS_API_URL              = var.flights_api_url
      HOTELS_API_URL               = var.hotels_api_url
      OPENAI_BASE_URL              = var.openai_base_url
      MODEL_NAME                   = var.model_name
      
      # RAG Strategies
      USE_CONTEXTUAL_EMBEDDINGS    = var.use_contextual_embeddings
      USE_HYBRID_SEARCH            = var.use_hybrid_search
      USE_AGENTIC_RAG              = var.use_agentic_rag
      USE_RERANKING                = var.use_reranking
      USE_KNOWLEDGE_GRAPH          = var.use_knowledge_graph
      USE_CODE_EXAMPLES            = var.use_code_examples
    }
  }

  tags = {
    Name = "crawl4ai-mcp-lambda"
  }
}

resource "aws_security_group" "lambda_sg" {
  name        = "lambda-sg"
  description = "Allows Lambda to connect to Neo4j and Aurora"
  vpc_id      = aws_vpc.main.id

  # Egress rules will be defined separately to break the dependency cycle

  # Ingress rules will be defined separately to break the dependency cycle

  tags = {
    Name = "lambda-sg"
  }
}


# --- Rules to break the cycle ---

# Egress rule for Lambda to talk to Neo4j
resource "aws_security_group_rule" "lambda_egress_neo4j" {
  type              = "egress"
  from_port         = 7687
  to_port           = 7687
  protocol          = "tcp"
  cidr_blocks       = [aws_vpc.main.cidr_block]
  security_group_id = aws_security_group.lambda_sg.id
}

# Egress rule for Lambda to talk to Aurora (references aurora_sg)
resource "aws_security_group_rule" "lambda_egress_aurora" {
  type                     = "egress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.aurora_sg.id
  security_group_id        = aws_security_group.lambda_sg.id
}

# Egress rule for Lambda to the Internet (via NAT Gateway)
resource "aws_security_group_rule" "lambda_egress_internet" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.lambda_sg.id
}

# Ingress rule for Lambda to allow self-referencing (needed for internal VPC communication)
resource "aws_security_group_rule" "lambda_ingress_self" {
  type              = "ingress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  self              = true
  security_group_id = aws_security_group.lambda_sg.id
}
