resource "aws_db_subnet_group" "crawl4ai_db_subnet_group" {
  name       = "crawl4ai-db-subnet-group"
  subnet_ids = [for s in aws_subnet.private : s.id] # Use all private subnets for multi-AZ coverage

  tags = {
    Name = "crawl4ai-db-subnet-group"
  }
}

resource "aws_rds_cluster" "crawl4ai_db" {
  cluster_identifier      = "crawl4ai-db"
  engine                  = "aurora-postgresql"
  engine_version          = "15.4" # A recent version supporting Serverless v2
  database_name           = var.db_name
  master_username         = var.db_username
  master_password         = var.db_master_password
  db_subnet_group_name    = aws_db_subnet_group.crawl4ai_db_subnet_group.name
  vpc_security_group_ids  = [aws_security_group.aurora_sg.id]
  skip_final_snapshot     = true
  
  # Serverless V2 Configuration
  serverlessv2_scaling_configuration {
    min_capacity = 0.5
    max_capacity = 1.0
  }

  tags = {
    Name = "crawl4ai-db-cluster"
  }
}

resource "aws_rds_cluster_instance" "crawl4ai_instance" {
  identifier              = "crawl4ai-db-instance"
  cluster_identifier      = aws_rds_cluster.crawl4ai_db.id
  instance_class          = "db.serverless"
  engine                  = aws_rds_cluster.crawl4ai_db.engine
  engine_version          = aws_rds_cluster.crawl4ai_db.engine_version
  publicly_accessible     = false

  tags = {
    Name = "crawl4ai-db-instance"
  }
}

resource "aws_security_group" "aurora_sg" {
  name        = "aurora-sg"
  description = "Security group for Aurora PostgreSQL cluster"
  vpc_id      = aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "aurora-sg"
  }
}


# Ingress rule for Aurora to allow connections from Lambda (references lambda_sg)
resource "aws_security_group_rule" "aurora_ingress_lambda" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.lambda_sg.id
  security_group_id        = aws_security_group.aurora_sg.id
}
