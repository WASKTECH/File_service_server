# 🏗️ Terraform Infrastructure — WASK File Service

This directory contains the complete Infrastructure-as-Code (IaC) for the **WASK Technologies Multi-Tenant File Service API** on AWS, built with **Terraform v1.8+**.

---

## 📁 Directory Structure

```
terraform/
├── main.tf                    # Root module — composes all 12 child modules
├── variables.tf               # Input variable declarations with defaults
├── outputs.tf                 # Infrastructure outputs (ALB DNS, ECR URL, etc.)
├── locals.tf                  # Common tags and computed values
├── providers.tf               # AWS provider configuration
├── versions.tf                # Terraform + provider version constraints
│
├── environments/              # Per-environment configurations
│   ├── dev/
│   │   ├── main.tf            # Calls root module with dev backend
│   │   ├── backend.tf         # Local state backend
│   │   └── terraform.tfvars   # Dev-specific values (micro DB, 1 task)
│   ├── staging/
│   │   ├── main.tf
│   │   ├── backend.tf
│   │   └── terraform.tfvars
│   └── production/
│       ├── main.tf
│       ├── backend.tf
│       └── terraform.tfvars
│
└── modules/                   # Reusable infrastructure modules
    ├── networking/            # VPC, Subnets, NAT, IGW, S3 VPC Endpoint
    ├── security/              # Security Groups (ALB → ECS → RDS)
    ├── ecr/                   # Elastic Container Registry
    ├── s3/                    # S3 Buckets (Storage + Access Logs)
    ├── secrets/               # AWS Secrets Manager
    ├── iam/                   # IAM Roles & Policies (Execution + Task)
    ├── rds/                   # RDS PostgreSQL 16
    ├── alb/                   # Application Load Balancer
    ├── ecs/                   # ECS Fargate (Cluster, Service, Task Def)
    ├── cloudwatch/            # Dashboard & Metric Alarms
    ├── acm/                   # ACM Certificate (conditional)
    └── route53/               # Route53 DNS (conditional)
```

---

## 🚀 Quick Start

```bash
# 1. Navigate to target environment
cd terraform/environments/dev

# 2. Initialize Terraform
terraform init

# 3. Preview changes
terraform plan -out=tfplan

# 4. Deploy infrastructure
terraform apply tfplan
```

---

## 📋 Input Variables

### Required Variables (set in `terraform.tfvars`)

| Variable | Type | Description | Dev Default |
|:---|:---|:---|:---|
| `environment` | string | Environment name | `"dev"` |
| `project_name` | string | Project name prefix | `"wasktech-file-service"` |
| `aws_region` | string | AWS Region | `"us-east-1"` |
| `vpc_cidr` | string | VPC CIDR block | `"10.0.0.0/16"` |
| `availability_zones` | list(string) | AZs to deploy across | `["us-east-1a", "us-east-1b"]` |

### Compute & Database

| Variable | Type | Description | Dev Default |
|:---|:---|:---|:---|
| `ecs_cpu` | number | Fargate CPU units | `512` (0.5 vCPU) |
| `ecs_memory` | number | Fargate memory (MB) | `1024` (1 GB) |
| `ecs_desired_count` | number | Number of ECS tasks | `1` |
| `ecs_min_capacity` | number | Min auto-scale capacity | `1` |
| `ecs_max_capacity` | number | Max auto-scale capacity | `4` |
| `db_instance_class` | string | RDS instance size | `"db.t4g.micro"` |
| `db_multi_az` | bool | Multi-AZ deployment | `false` |

### Networking & Domain

| Variable | Type | Description | Dev Default |
|:---|:---|:---|:---|
| `enable_single_nat_gateway` | bool | Use 1 NAT (cost savings) | `true` |
| `enable_custom_domain` | bool | Request ACM cert for `domain_name` | `true` (dev) |
| `domain_name` | string | Custom domain name | `"fileservice.wasktechnologies.com"` |
| `route53_zone_id` | string | Route53 zone ID (empty = external DNS) | `""` |
| `attach_acm_certificate` | bool | Attach cert to ALB HTTPS after DNS validation | `false` until ACM CNAME exists |

---

## 📤 Outputs

After `terraform apply`, these values are available:

| Output | Description | Example |
|:---|:---|:---|
| `alb_dns_name` | ALB DNS endpoint | `wasktech-file-service-dev-alb-XXX.us-east-1.elb.amazonaws.com` |
| `api_url` | Full API URL | `https://fileservice.wasktechnologies.com` |
| `acm_validation_records` | ACM DNS validation CNAMEs (external DNS) | `[{name, type, value}]` |
| `acm_certificate_status` | ACM certificate status | `PENDING_VALIDATION` / `ISSUED` |
| `ecr_repository_url` | ECR Docker repository | `091869721140.dkr.ecr.us-east-1.amazonaws.com/wasktech-file-service-api-dev` |
| `s3_bucket_name` | S3 storage bucket | `wasktech-file-service-storage-dev-091869721140` |
| `rds_endpoint` | PostgreSQL endpoint | `wasktech-file-service-dev-db.xxx.rds.amazonaws.com:5432` |
| `ecs_cluster_name` | ECS cluster name | `wasktech-file-service-dev-cluster` |
| `ecs_service_name` | ECS service name | `wasktech-file-service-dev-service` |
| `cloudwatch_dashboard_name` | Dashboard name | `wasktech-file-service-dev-dashboard` |
| `secrets_manager_arn` | Secrets ARN | `arn:aws:secretsmanager:us-east-1:...` |

---

## 🧩 Module Reference

### networking

Creates the complete VPC network topology with public, private application, and private database subnets across multiple AZs.

**Key Resources**: VPC, 6 Subnets, Internet Gateway, NAT Gateway(s), Route Tables, S3 VPC Gateway Endpoint

**Inputs**: `vpc_cidr`, `availability_zones`, `enable_single_nat_gateway`

---

### security

Creates three chained security groups enforcing strict network segmentation.

**Chain**: `Internet → ALB SG (80/443) → ECS SG (8000) → RDS SG (5432)`

Each group references the source security group (not CIDRs) for dynamic, instance-aware access control.

---

### ecr

Private Docker container registry with automated lifecycle management.

**Features**: Image scanning on push, lifecycle policy retaining last 10 images, image tag mutability

---

### s3

Dual-bucket setup: one for application file storage, one for ALB access logs.

**Storage Bucket Features**: Versioning, AES-256 encryption, CORS for browser uploads, lifecycle rules, public access block, TLS-only bucket policy

---

### secrets

AWS Secrets Manager secret with auto-generated database password.

**Stored Secrets**: `DATABASE_URL`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`

---

### iam

Least-privilege IAM roles for ECS Fargate.

**Execution Role**: ECR pull, Secrets Manager read, CloudWatch logs write
**Task Role**: S3 GetObject/PutObject/DeleteObject/HeadObject on designated bucket only

---

### rds

PostgreSQL 16 database with security hardening.

**Features**: Automated backups (7-day retention), storage encryption, `rds.force_ssl=1`, `log_statement=all`, configurable Multi-AZ

---

### alb

Application Load Balancer with health-checked target group.

**Health Check**: `GET /api/v1/health` every 30 seconds, 3 healthy threshold, 3 unhealthy threshold
**Listeners**: HTTP (port 80) forwards to ECS until the ACM cert is attached, then redirects to HTTPS (port 443)

---

### ecs

ECS Fargate cluster with container service and optional auto scaling.

**Features**: Container health checks, deployment circuit breaker with rollback, Secrets Manager injection, auto-created CloudWatch log group, auto scaling on CPU/Memory (production only)

---

### cloudwatch

Observability dashboard and metric alarms.

**Dashboard Widgets**: ECS CPU/Memory, ALB requests/response time, ALB 5XX errors, RDS CPU/storage
**Alarms**: CPU >80%, Memory >80%, 5XX >10/5min, RDS storage <2GB

---

### acm (conditional)

AWS Certificate Manager SSL certificate with DNS validation.

**Created When**: `enable_custom_domain = true`

When `route53_zone_id` is empty, Terraform outputs `acm_validation_records` for the external DNS provider. Set `attach_acm_certificate = true` after those records exist to wait for issuance and attach HTTPS.

---

### route53 (conditional)

Route53 alias record pointing the custom domain to the ALB.

**Created When**: `enable_custom_domain = true` and `route53_zone_id` is set

---

## 🏷️ Resource Tagging

All resources receive consistent tags defined in `locals.tf`:

```hcl
common_tags = {
  Project     = "wasktech-file-service"
  Environment = var.environment
  ManagedBy   = "Terraform"
  Repository  = "WASKTECH/File_service_server"
}
```

Additional tags from the environment `terraform.tfvars` are merged (e.g., `Owner`, `CostCenter`).

---

## ⚠️ IAM Permission Notes

The following workarounds are applied for developer-level IAM accounts:

| Issue | Workaround |
|:---|:---|
| `logs:PutRetentionPolicy` denied | CloudWatch log group auto-created by ECS (`awslogs-create-group = true`) instead of Terraform |
| `application-autoscaling:ListTagsForResource` denied | Auto scaling disabled for dev/staging (`count = 0`), enabled only for production |

For full Terraform management, add `CloudWatchLogsFullAccess` and `AWSKeyManagementServicePowerUser` policies.

---

## 🗑️ Destroying Infrastructure

```bash
cd terraform/environments/dev
terraform destroy
```

If S3 buckets block destruction (non-empty):
```bash
aws s3 rm s3://<BUCKET_NAME> --recursive
terraform destroy
```
