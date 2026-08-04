# 🚀 Deployment Guide — WASK File Service Infrastructure & Application

This guide provides complete step-by-step instructions for deploying, updating, and managing the Multi-Tenant File Service API on AWS infrastructure.

---

## 📋 Prerequisites

### Required Tools

| Tool | Minimum Version | Installation |
|:-----|:---------------|:------------|
| **Terraform** | v1.8.0+ | [terraform.io/downloads](https://developer.hashicorp.com/terraform/downloads) |
| **AWS CLI** | v2.x | [aws.amazon.com/cli](https://aws.amazon.com/cli/) |
| **Docker** | v24.x+ | [docker.com/get-started](https://www.docker.com/get-started/) |
| **Git** | v2.x+ | [git-scm.com](https://git-scm.com/) |

### Required AWS IAM Policies

Your IAM user or role must have the following managed policies attached:

| Policy Name | Covers |
|:---|:---|
| `AmazonEC2FullAccess` | VPC, Subnets, NAT, Security Groups, ALB |
| `AmazonECS_FullAccess` | ECS Clusters, Services, Task Definitions |
| `AmazonRDSFullAccess` | RDS PostgreSQL instances |
| `AmazonEC2ContainerRegistryFullAccess` | ECR Repository management |
| `AmazonS3FullAccess` | S3 Bucket operations |
| `IAMFullAccess` | IAM Role and Policy creation |
| `SecretsManagerReadWrite` | Secrets Manager operations |

> **Note**: For production environments, also add `CloudWatchLogsFullAccess` and `AWSKeyManagementServicePowerUser` to enable custom KMS encryption and log group management.

---

## 🛠️ First-Time Infrastructure Deployment

### Step 1: Clone the Repository

```bash
git clone https://github.com/WASKTECH/File_service_server.git
cd File_service_server
```

### Step 2: Configure AWS Credentials

```bash
aws configure
# AWS Access Key ID: <your-key-id>
# AWS Secret Access Key: <your-secret-key>
# Default region: us-east-1
# Default output: json
```

Verify credentials:
```bash
aws sts get-caller-identity
```

### Step 3: Select Target Environment

Choose the environment to deploy. For new projects, start with **dev**:

```bash
cd terraform/environments/dev
```

| Environment | Config File | Monthly Cost | Use Case |
|:---|:---|:---|:---|
| `dev` | `environments/dev/terraform.tfvars` | ~$101 | Development & testing |
| `staging` | `environments/staging/terraform.tfvars` | ~$101 | Pre-production validation |
| `production` | `environments/production/terraform.tfvars` | ~$619 | Live production traffic |

### Step 4: Initialize Terraform

```bash
terraform init
```

Expected output:
```
Terraform has been successfully initialized!
```

### Step 5: Review the Execution Plan

```bash
terraform plan -out=tfplan
```

Review the resources that will be created. For a fresh dev deployment, expect approximately **35+ resources**.

### Step 6: Apply Infrastructure

```bash
terraform apply tfplan
```

> **⏱ Expected Duration**: 8–12 minutes (RDS creation takes ~8 minutes)

### Step 7: Record the Outputs

After successful apply, Terraform outputs critical infrastructure values:

```
alb_dns_name       = "wasktech-file-service-dev-alb-XXXXXXXXX.us-east-1.elb.amazonaws.com"
api_url            = "http://wasktech-file-service-dev-alb-XXXXXXXXX.us-east-1.elb.amazonaws.com"
ecr_repository_url = "091869721140.dkr.ecr.us-east-1.amazonaws.com/wasktech-file-service-api-dev"
rds_endpoint       = "wasktech-file-service-dev-db.xxxxx.us-east-1.rds.amazonaws.com:5432"
s3_bucket_name     = "wasktech-file-service-storage-dev-091869721140"
```

Save these — you'll need them for application deployment.

---

## 🐳 Application Deployment (Docker → ECR → ECS)

### Step 1: Authenticate Docker with ECR

```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com
```

Replace `<ACCOUNT_ID>` with your AWS Account ID (visible in `terraform output`).

### Step 2: Build the Docker Image

```bash
docker build -t wasktech-file-service-api .
```

### Step 3: Tag the Image for ECR

```bash
# For dev environment:
docker tag wasktech-file-service-api:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/wasktech-file-service-api-dev:latest

# For production:
docker tag wasktech-file-service-api:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/wasktech-file-service-api-production:latest
```

### Step 4: Push Image to ECR

```bash
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/wasktech-file-service-api-dev:latest
```

### Step 5: Deploy to ECS (Force New Deployment)

```bash
aws ecs update-service \
    --cluster wasktech-file-service-dev-cluster \
    --service wasktech-file-service-dev-service \
    --force-new-deployment \
    --region us-east-1
```

ECS will pull the new image, start a new task, register it with the ALB, drain the old task, and terminate it — zero downtime.

### Step 6: Monitor Deployment Progress

```bash
aws ecs wait services-stable \
    --cluster wasktech-file-service-dev-cluster \
    --services wasktech-file-service-dev-service \
    --region us-east-1
```

### Step 7: Verify Application Health

```bash
curl -i http://<ALB_DNS_NAME>/api/v1/health
```

Expected response:
```json
HTTP/1.1 200 OK
Content-Type: application/json

{"status": "healthy", "service": "File Service API"}
```

---

## 🔄 CI/CD Automated Deployments

Once the infrastructure is deployed, application updates are automated via GitHub Actions.

### GitHub Repository Secrets Required

Navigate to **GitHub → Settings → Secrets and variables → Actions** and add:

| Secret Name | Value |
|:---|:---|
| `AWS_ACCESS_KEY_ID` | Your AWS Access Key ID |
| `AWS_SECRET_ACCESS_KEY` | Your AWS Secret Access Key |

### How CI/CD Works

| Trigger | Branch | Action |
|:---|:---|:---|
| Push to `staging` | staging | Build → Test → Deploy to **staging** ECS |
| Push to `main` | main | Build → Test → Deploy to **production** ECS |
| Manual dispatch | any | Trigger via GitHub Actions UI |

### Pipeline Stages

1. **Test & Scan**: Install dependencies → Run Pytest with coverage
2. **Build & Deploy**: Build Docker image → Push to ECR → Update ECS Task Definition → Deploy to ECS → Health check (10 retries)

---

## 🌐 Adding a Custom Domain (When Ready)

The infrastructure supports adding a custom domain at any time:

### Step 1: Create a Route53 Hosted Zone

```bash
aws route53 create-hosted-zone \
    --name wasktech.com \
    --caller-reference "$(date +%s)"
```

### Step 2: Copy the Zone ID

```bash
aws route53 list-hosted-zones-by-name \
    --dns-name wasktech.com \
    --query "HostedZones[0].Id" \
    --output text
```

### Step 3: Update the Environment Config

Edit the target environment's `terraform.tfvars`:

```hcl
enable_custom_domain = true
domain_name          = "api.wasktech.com"
route53_zone_id      = "Z0ACTUAL_ZONE_ID_HERE"
```

### Step 4: Apply Changes

```bash
terraform plan -out=tfplan
terraform apply tfplan
```

Terraform will automatically:
- Request an ACM SSL certificate
- Validate it via DNS
- Create a Route53 alias record pointing to the ALB
- Add an HTTPS listener with the SSL certificate
- Redirect HTTP → HTTPS

---

## 🧹 Infrastructure Teardown

### Destroy a Specific Environment

```bash
cd terraform/environments/dev
terraform destroy
```

> **⚠ Warning**: This destroys ALL resources including the RDS database. Ensure backups are taken first.

### Destroy Order Safety

Terraform handles dependency ordering automatically. However, if destroy fails:

1. Manually empty the S3 buckets first:
   ```bash
   aws s3 rm s3://wasktech-file-service-storage-dev-ACCOUNT_ID --recursive
   aws s3 rm s3://wasktech-file-service-logs-dev-ACCOUNT_ID --recursive
   ```
2. Re-run `terraform destroy`

---

## ✅ Post-Deployment Checklist

- [ ] `terraform apply` completed with zero errors
- [ ] Docker image built and pushed to ECR
- [ ] ECS service updated and running with the new image
- [ ] Health check returns HTTP 200 at `/api/v1/health`
- [ ] Seed the first tenant application using `python seed_app.py`
- [ ] Test file upload/download lifecycle end-to-end
- [ ] Verify CloudWatch Dashboard is populating metrics
- [ ] GitHub Secrets configured for CI/CD automation
- [ ] Team notified with ALB DNS endpoint
