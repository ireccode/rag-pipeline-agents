#!/bin/bash

# --- Configuration ---
REGION="ap-southeast-2"
REPO_NAME="crawl4ai-mcp"
IMAGE_TAG="crawl4ai_mcp:latest"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME"

# --- Step 1: Build Docker Image (Requires successful completion on user's machine) ---
echo "--- Step 1: Building Docker Image ---"
# NOTE: The local build failed in the sandbox environment.
# Please ensure you have Docker installed and run this command from the repository root.
# cd /path/to/rag-pipeline-agents/
# docker build -t $IMAGE_TAG .
# Check if the image already exists locally.
if docker images -q $IMAGE_TAG > /dev/null; then
    echo "Image $IMAGE_TAG already exists locally. Skipping build."
else
    echo "Image $IMAGE_TAG not found locally. Starting build..."
    # Navigate to the repository root to ensure the Docker build context is correct (where pyproject.toml is located)
    (cd .. && docker build -t $IMAGE_TAG .)
fi

# --- Step 2: ECR Configuration and Push ---
echo "--- Step 2: Authenticating and Pushing to ECR ---"
# Check if ECR repository exists (Terraform will create it, but we need the URI now)
# We will rely on Terraform to create the repository, but we need to login now.
# The ECR repository URL will be available after 'terraform apply'.
# For now, we use the calculated URI.

# ECR Login
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Tag the image
docker tag $IMAGE_TAG $ECR_URI:latest

# Push the image
docker push $ECR_URI:latest

# --- Step 3: Terraform Stage 1: Create ECR Repository ---
echo "--- Step 3: Initializing Terraform ---"
# NOTE: Before running 'terraform init', you must manually create the S3 bucket 
# and DynamoDB table specified in main.tf for remote state.
terraform init

echo "--- Step 4: Applying Terraform Stage 1 (ECR Creation) ---"
# Apply only the ECR resource. This requires the repository_name variable.
terraform apply -auto-approve -target=aws_ecr_repository.crawl4ai_mcp \
# Variables are loaded from terraform.tfvars (as confirmed by user)

# --- Step 5: ECR Configuration and Push ---
echo "--- Step 5: Authenticating and Pushing to ECR ---"
# ECR Login
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Tag the image
docker tag $IMAGE_TAG $ECR_URI:latest

# Push the image
docker push $ECR_URI:latest

# --- Step 6: Terraform Stage 2: Deploy Remaining Infrastructure ---
echo "--- Step 6: Deploying Remaining Infrastructure (Lambda, DBs, API Gateway) ---"
# Apply the rest of the configuration.
terraform apply -auto-approve \
# Variables are loaded from terraform.tfvars (as confirmed by user)

echo "--- Deployment Complete. Outputs: ---"
terraform output

