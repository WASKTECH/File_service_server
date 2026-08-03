# 🚀 Deployment Guide - AWS Infrastructure & Application

This guide details how DevOps and Platform Engineers can deploy, update, and manage the **Multi-Tenant File Service API** infrastructure and application on AWS.

---

## 📋 Prerequisites

Ensure the following tools are installed on your local workstation or CI/CD runner:

- **Terraform v1.8.0+**
- **AWS CLI v2**
- **Docker Desktop / Docker Engine**
- **Git**

---

## 🛠️ Step-by-Step Deployment Instructions

### Step 1: Clone Repository & Select Environment

```bash
git clone https://github.com/WASKTECH/File_service_server.git
cd File_service_server
```

Choose your target environment (`dev`, `staging`, or `production`):
```bash
cd terraform/environments/dev
```

---

### Step 2: Initialize Remote State (S3 & DynamoDB)

Create the initial backend S3 bucket and DynamoDB locking table if deploying for the first time:

```bash
aws s3api create-bucket --bucket wasktech-tfstate-dev-us-east-1 --region us-east-1
aws dynamodb create-table \
    --table-name wasktech-tflocks-dev \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1
```

Now initialize Terraform:
```bash
terraform init
```

---

### Step 3: Validate & Plan Infrastructure

```bash
terraform fmt -check
terraform validate
terraform plan -out=tfplan
```

---

### Step 4: Apply Infrastructure

```bash
terraform apply tfplan
```

*Outputs produced*:
- `alb_dns_name`: Load balancer DNS endpoint
- `ecr_repository_url`: ECR Docker repository URL
- `s3_bucket_name`: Storage bucket name
- `rds_endpoint`: PostgreSQL connection endpoint
- `secrets_manager_arn`: AWS Secrets Manager Secret ARN

---

### Step 5: Build & Push Docker Container to ECR

```bash
# 1. Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

# 2. Build Docker Image
docker build -t wasktech-file-service-api:dev .

# 3. Tag Docker Image
docker tag wasktech-file-service-api:dev <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/wasktech-file-service-api-dev:latest

# 4. Push Image
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/wasktech-file-service-api-dev:latest
```

---

### Step 6: Force ECS Deployment

```bash
aws ecs update-service \
    --cluster wasktech-file-service-dev-cluster \
    --service wasktech-file-service-dev-service \
    --force-new-deployment \
    --region us-east-1
```

---

### Step 7: Verify Application Health

```bash
curl -i http://<ALB_DNS_NAME>/api/v1/health
```

Expected output:
```json
HTTP/1.1 200 OK
Content-Type: application/json

{"status": "healthy", "service": "File Service API"}
```

---

## 🧹 Infrastructure Destruction Command

To completely destroy all provisioned infrastructure (e.g. for dev teardowns):

```bash
terraform destroy -auto-approve
```
