terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # NOTE: You must create the S3 bucket and DynamoDB table manually before running 'terraform init'.
  # Replace 'your-terraform-state-bucket' with your actual bucket name.
  # The DynamoDB table 'terraform-lock' is for state locking and must also be created.
  backend "s3" {
    bucket         = "in-crawl4ai-mcp-terraform-state-bucket-456434" 
    key            = "crawl4ai-mcp/terraform.tfstate"
    region         = "ap-southeast-2"
    encrypt        = true
    dynamodb_table = "terraform-lock"
  }
}

provider "aws" {
  region = var.region
}

