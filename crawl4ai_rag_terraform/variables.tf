variable "region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "ap-southeast-2"
}

variable "repository_name" {
  description = "Name for the ECR repository"
  type        = string
  default     = "crawl4ai-mcp"
}

variable "neo4j_password" {
  description = "Password for the Neo4j database"
  type        = string
  sensitive   = true
}

variable "source_image_tag" {
  description = "The tag of the local Docker image to push to ECR"
  type        = string
  default     = "crawl4ai_mcp:latest"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR block for the public subnet"
  type        = string
  default     = "10.0.1.0/24"
}

variable "private_subnet_cidr" {
  description = "CIDR block for the private subnet"
  type        = string
  default     = "10.0.2.0/24"
}

variable "instance_type" {
  description = "EC2 instance type for Neo4j"
  type        = string
  default     = "t4g.small" # Free-tier eligible and ARM for better cost
}

variable "key_name" {
  description = "The name of the SSH key pair to use for the EC2 instance"
  type        = string
  default     = "terraform-key"
}


variable "db_master_password" {
  description = "Master password for the Aurora PostgreSQL database"
  type        = string
  sensitive   = true
}

variable "db_name" {
  description = "Name of the Aurora PostgreSQL database"
  type        = string
  default     = "crawl4ai"
}

variable "db_username" {
  description = "Master username for the Aurora PostgreSQL database"
  type        = string
  default     = "crawl4aiadmin"
}


variable "openai_api_key" {
  description = "OpenAI API key for the embedding model"
  type        = string
  sensitive   = true
}

variable "model_choice" {
  description = "The LLM to use for summaries and contextual embeddings"
  type        = string
  default     = "gpt-4.1-nano"
}

variable "corpus_url" {
  description = "The URL of the corpus to crawl"
  type        = string
  default     = "https://docs.aws.amazon.com/index.html" # Placeholder
}

variable "flights_api_url" {
  description = "The URL of the flights API for the agent"
  type        = string
  default     = "http://mock-flights-api.com" # Placeholder
}

variable "hotels_api_url" {
  description = "The URL of the hotels API for the agent"
  type        = string
  default     = "http://mock-hotels-api.com" # Placeholder
}

variable "openai_base_url" {
  description = "The base URL for OpenAI (leave empty for default)"
  type        = string
  default     = ""
}

variable "model_name" {
  description = "The Azure dpl model name, leave empty for default model gpt-4.1-mini"
  type        = string
  default     = ""
}

variable "use_contextual_embeddings" {
  description = "Enhances embeddings with contextual information"
  type        = string
  default     = "false"
}

variable "use_hybrid_search" {
  description = "Combines vector similarity search with keyword search"
  type        = string
  default     = "false"
}

variable "use_agentic_rag" {
  description = "Enables code example extraction, storage, and specialized code search functionality"
  type        = string
  default     = "false"
}

variable "use_reranking" {
  description = "Applies cross-encoder reranking to improve search result relevance"
  type        = string
  default     = "false"
}

variable "use_knowledge_graph" {
  description = "Enables AI hallucination detection and repository parsing tools using Neo4j"
  type        = string
  default     = "true" # Setting to true as Neo4j is provisioned
}


variable "use_code_examples" {
  description = "Enables specialized code search functionality (if different from USE_AGENTIC_RAG)"
  type        = string
  default     = "false"
}


variable "image_digest" {
  description = "The SHA256 digest of the Docker image in ECR (e.g., sha256:bb2e999a57b203f4a529b6b37922480f816f67eb23707115474234281d813d9d)"
  type        = string
  default     = "sha256:c13fa62a2698826eb243347105c2d8f27be5e0601cc12398a30b97765837b379" # Using the digest from the user's latest push
}
