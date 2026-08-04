# 🏛️ AWS Cloud Architecture — WASK Multi-Tenant File Service API

This document presents the complete architectural design of the AWS infrastructure hosting the **WASK Technologies Multi-Tenant File Service API**, built and managed with Terraform.

---

## 📐 System Architecture Overview

```
                                    ┌────────────────────────────┐
                                    │    Internet Clients        │
                                    │  (Web / Mobile / Services) │
                                    └──────────┬─────────────────┘
                                               │
                                         HTTP (Port 80)
                                      [HTTPS 443 when domain
                                       is provisioned later]
                                               │
                                               ▼
                          ┌────────────────────────────────────────────┐
                          │       Application Load Balancer (ALB)      │
                          │  (Public Subnets — us-east-1a, us-east-1b)│
                          │  Health Check: GET /api/v1/health (30s)    │
                          └────────────────┬───────────────────────────┘
                                           │
                                    HTTP (Port 8000)
                                           │
                          ┌────────────────┼────────────────┐
                          ▼                                 ▼
                ┌──────────────────┐              ┌──────────────────┐
                │   ECS Fargate    │              │   ECS Fargate    │
                │   Task (AZ-1a)  │              │   Task (AZ-1b)  │
                │  FastAPI + Uvi  │              │  FastAPI + Uvi  │
                └───────┬──┬──────┘              └───────┬──┬──────┘
                        │  │                             │  │
          ┌─────────────┘  └────────┐      ┌─────────────┘  └──────────┐
          ▼                         ▼      ▼                           ▼
┌──────────────────┐    ┌───────────────────────┐           ┌──────────────────┐
│  AWS Secrets     │    │  Amazon S3 Bucket     │           │  Amazon RDS      │
│  Manager         │    │  (File Storage)       │           │  PostgreSQL 16   │
│  (DB Creds +     │    │  Versioned + Encrypted│           │  (Private DB     │
│   App Secrets)   │    │  Via VPC Endpoint     │           │   Subnets)       │
└──────────────────┘    └───────────────────────┘           └──────────────────┘
                                    ▲
                                    │
                          S3 VPC Gateway Endpoint
                       (No NAT / No Internet routing)
```

---

## 🧩 Terraform Module Architecture

The infrastructure is composed of **12 reusable Terraform modules**, each with single-responsibility design:

| # | Module | Purpose | Key Resources |
|:--|:-------|:--------|:-------------|
| 1 | **networking** | Network foundation | VPC, 2 Public Subnets, 2 Private App Subnets, 2 Private DB Subnets, Internet Gateway, NAT Gateway, Route Tables, S3 VPC Gateway Endpoint |
| 2 | **security** | Network access control | 3 Security Groups (ALB → ECS → RDS chain) |
| 3 | **ecr** | Container registry | Private ECR Repository, Lifecycle Policy (keep last 10 images) |
| 4 | **s3** | File storage | Storage Bucket (versioned, encrypted, CORS, lifecycle), Access Logs Bucket |
| 5 | **secrets** | Credential management | Secrets Manager Secret with auto-generated DB password |
| 6 | **iam** | Access control | ECS Execution Role, ECS Task Role, S3 policy, Secrets policy |
| 7 | **rds** | Database | PostgreSQL 16 instance, Parameter Group, Subnet Group |
| 8 | **alb** | Load balancing | Application Load Balancer, Target Group, HTTP/HTTPS Listeners |
| 9 | **ecs** | Compute | ECS Cluster, Fargate Task Definition, Service, Auto Scaling (production only) |
| 10 | **cloudwatch** | Observability | Dashboard, CPU/Memory/5XX/RDS Storage Alarms |
| 11 | **acm** | SSL certificates | ACM Certificate + DNS Validation (conditional) |
| 12 | **route53** | DNS management | Route53 Alias Record for ALB (conditional) |

### Module Dependency Graph

```
networking ──► security ──► alb ──────────────────────────────────────┐
    │                         ▲                                       │
    │              ┌──────────┘                                       │
    │              │                                                  ▼
    ├──► rds ──► secrets ──► iam ──► ecs ──► cloudwatch              │
    │                                  ▲                              │
    │                                  │                              │
    └──────────────────────────────────┘                              │
                                                                      │
ecr (independent) ◄───────────────────────────────────────────────────┘
s3  (independent) ────► iam (S3 bucket ARN for task role policy)
acm + route53 (conditional — only when enable_custom_domain = true)
```

---

## 🌐 Network Topology

### VPC Design — `10.0.0.0/16`

| Subnet Type | CIDR (AZ-1a) | CIDR (AZ-1b) | Purpose | Internet Access |
|:---|:---|:---|:---|:---|
| **Public** | `10.0.1.0/24` | `10.0.2.0/24` | ALB only | Direct via IGW |
| **Private App** | `10.0.11.0/24` | `10.0.12.0/24` | ECS Fargate Tasks | Outbound via NAT Gateway |
| **Private DB** | `10.0.21.0/24` | `10.0.22.0/24` | RDS PostgreSQL | No internet access |

### Key Networking Features

- **Single NAT Gateway** (dev/staging) or **Multi-AZ NAT** (production) for cost optimization
- **S3 VPC Gateway Endpoint**: All ECS ↔ S3 traffic stays on the AWS backbone — zero NAT charges for file operations
- **No public IPs** on ECS tasks or RDS instances

---

## 🔒 Defense-in-Depth Security

### Layer 1: Network Isolation (Security Groups)

```
Internet ──► ALB SG (Port 80/443 from 0.0.0.0/0)
                    │
                    ▼
             ECS SG (Port 8000 ONLY from ALB SG)
                    │
                    ▼
             RDS SG (Port 5432 ONLY from ECS SG)
```

Each security group references the **source security group** (not CIDR blocks), creating a strict chain of trust.

### Layer 2: IAM Least Privilege

| Role | Permissions | What It Cannot Do |
|:---|:---|:---|
| **ECS Execution Role** | Pull ECR images, read Secrets Manager, create CloudWatch log streams | Cannot access S3, cannot modify secrets |
| **ECS Task Role** | S3 `GetObject`, `PutObject`, `DeleteObject`, `HeadObject` on designated bucket only | Cannot list all buckets, cannot access other AWS services |

### Layer 3: Data Encryption

| Data State | Encryption Method |
|:---|:---|
| **S3 Objects at Rest** | AES-256 Server-Side Encryption (SSE-S3) |
| **RDS Storage at Rest** | AWS-managed encryption |
| **Secrets at Rest** | AWS Secrets Manager default encryption |
| **S3 in Transit** | TLS enforced via `aws:SecureTransport` bucket policy |
| **RDS in Transit** | `rds.force_ssl = 1` parameter enforced |

### Layer 4: Application-Level Security

- **SHA-256 hashed API keys** with constant-time comparison (`secrets.compare_digest`)
- **UUIDv4 public identifiers** preventing sequential enumeration
- **Database-level tenant isolation** (`WHERE app_id = :caller_app_id` on every query)
- **S3 key namespacing** (`{app_id}/{uuid}-{filename}`)

---

## 🌍 Multi-Environment Strategy

| Setting | Dev | Staging | Production |
|:---|:---|:---|:---|
| **ECS CPU / Memory** | 512 / 1024 MB | 512 / 1024 MB | 1024 / 2048 MB |
| **ECS Tasks** | 1 (no auto scaling) | 1 (no auto scaling) | 2 (auto scales 2–10) |
| **RDS Instance** | `db.t4g.micro` | `db.t4g.micro` | `db.t4g.small` |
| **RDS Multi-AZ** | ❌ | ❌ | ✅ |
| **NAT Gateways** | 1 (shared) | 1 (shared) | 2 (per AZ) |
| **Custom Domain** | ❌ | ❌ | When provisioned |
| **Deletion Protection** | ❌ | ❌ | ✅ |
| **Est. Monthly Cost** | ~$101 | ~$101 | ~$619 |

---

## ⚡ High Availability & Resiliency

- **Multi-AZ Load Balancing**: ALB distributes across 2 Availability Zones
- **ECS Health Checks**: ALB polls `/api/v1/health` every 30 seconds; unhealthy containers are auto-replaced
- **Deployment Circuit Breaker**: ECS automatically rolls back failed deployments
- **RDS Multi-AZ** (production): Synchronous standby replica with <60s automatic failover
- **RDS Automated Backups**: 7-day retention with Point-in-Time Recovery (PITR)
- **S3 Versioning**: Enabled — accidental deletions are recoverable

---

## 📊 Observability Stack

### CloudWatch Dashboard

The auto-provisioned dashboard (`wasktech-file-service-{env}-dashboard`) displays:

- ECS CPU & Memory Utilization
- ALB Request Count & Target Response Time
- ALB HTTP 5XX Error Rate
- RDS CPU Utilization & Free Storage Space

### CloudWatch Alarms

| Alarm | Condition | Action |
|:---|:---|:---|
| **ECS High CPU** | CPU > 80% for 5 minutes | Alert |
| **ECS High Memory** | Memory > 80% for 5 minutes | Alert |
| **ALB High 5XX** | > 10 5XX errors in 5 minutes | Alert |
| **RDS Low Storage** | Free storage < 2 GB | Alert |

---

## 🚀 CI/CD Pipeline Architecture

### Workflow 1: `app-deploy.yml` — Application Deployment

```
Push to main/staging
        │
        ▼
┌─────────────────┐    ┌────────────────────────────────────────┐
│ test-and-scan   │───►│ build-and-deploy                       │
│ - Install deps  │    │ - Build Docker image                   │
│ - Run Pytest    │    │ - Push to ECR (SHA + latest tag)       │
│ - Code coverage │    │ - Update ECS Task Definition           │
└─────────────────┘    │ - Deploy to ECS (wait for stability)   │
                       │ - Health check probe (10 retries)      │
                       └────────────────────────────────────────┘
```

### Workflow 2: `terraform-ci-cd.yml` — Infrastructure Changes

```
Pull Request                          Push to main
     │                                     │
     ▼                                     ▼
┌────────────┐                      ┌─────────────┐
│ Plan Only  │                      │ Plan + Apply │
│ terraform  │                      │ terraform    │
│ plan       │                      │ apply        │
└────────────┘                      └─────────────┘
```

---

## 📁 Terraform File Structure

```
terraform/
├── main.tf                        # Root module composition (all 12 modules)
├── variables.tf                   # Input variable declarations
├── outputs.tf                     # Infrastructure output values
├── locals.tf                      # Common tags and computed values
├── providers.tf                   # AWS provider configuration
├── versions.tf                    # Terraform and provider version constraints
├── environments/
│   ├── dev/
│   │   ├── main.tf                # Dev environment root (calls parent module)
│   │   ├── backend.tf             # Local state backend
│   │   └── terraform.tfvars       # Dev-specific variable values
│   ├── staging/
│   │   ├── main.tf
│   │   ├── backend.tf
│   │   └── terraform.tfvars
│   └── production/
│       ├── main.tf
│       ├── backend.tf
│       └── terraform.tfvars
└── modules/
    ├── networking/                 # VPC, Subnets, NAT, IGW, S3 Endpoint
    ├── security/                   # Security Groups (ALB, ECS, RDS)
    ├── ecr/                        # Elastic Container Registry
    ├── s3/                         # S3 Buckets (Storage + Logs)
    ├── secrets/                    # AWS Secrets Manager
    ├── iam/                        # IAM Roles & Policies
    ├── rds/                        # RDS PostgreSQL 16
    ├── alb/                        # Application Load Balancer
    ├── ecs/                        # ECS Fargate Cluster & Service
    ├── cloudwatch/                 # Dashboard & Metric Alarms
    ├── acm/                        # ACM SSL Certificate (conditional)
    └── route53/                    # DNS Alias Record (conditional)
```
