# 💰 AWS Monthly Cost Estimation — WASK File Service Infrastructure

This document provides estimated monthly AWS costs for each environment tier. Costs are based on **US-East-1 (N. Virginia)** pricing as of August 2026 and represent on-demand pricing without Reserved Instance discounts.

---

## 📊 Cost Summary by Environment

| Environment | Monthly Estimate | Annual Estimate | Key Difference |
|:---|:---|:---|:---|
| **Dev** | **~$101/month** | ~$1,212/year | Single NAT, single task, micro DB |
| **Staging** | **~$101/month** | ~$1,212/year | Same as dev |
| **Production** | **~$619/month** | ~$7,428/year | Multi-AZ, 2 NATs, 2 tasks, small DB |

---

## 🧾 Detailed Cost Breakdown — Dev Environment

| AWS Service | Resource | Specification | Monthly Cost |
|:---|:---|:---|---:|
| **NAT Gateway** | 1x NAT Gateway | Hourly + data processing | $34.00 |
| **ALB** | Application Load Balancer | Hourly + LCU charges | $18.00 |
| **ECS Fargate** | 1 task (0.5 vCPU / 1 GB) | 24/7 uptime | $19.00 |
| **RDS PostgreSQL** | db.t4g.micro (Single-AZ) | 20 GB gp3 storage | $13.00 |
| **S3** | Storage + Requests | Minimal in dev | $1.00 |
| **Secrets Manager** | 1 secret | Per-secret + API calls | $0.40 |
| **ECR** | Docker image storage | ~500 MB stored | $0.50 |
| **CloudWatch** | Dashboard + 4 alarms | Metrics + alarms | $3.00 |
| **Elastic IP** | 1 (for NAT Gateway) | Static allocation | $3.60 |
| **Data Transfer** | Internet egress | ~5 GB/month estimate | $5.00 |
| **VPC Endpoint** | S3 Gateway Endpoint | **Free** | $0.00 |
| | | **Total** | **~$101** |

---

## 🧾 Detailed Cost Breakdown — Production Environment

| AWS Service | Resource | Specification | Monthly Cost |
|:---|:---|:---|---:|
| **NAT Gateway** | 2x NAT Gateways (Multi-AZ) | Hourly + data processing | $68.00 |
| **ALB** | Application Load Balancer | Hourly + higher LCU | $22.00 |
| **ECS Fargate** | 2 tasks (1 vCPU / 2 GB each) | 24/7, auto-scales to 10 | $75.00 |
| **RDS PostgreSQL** | db.t4g.small (Multi-AZ) | 50 GB gp3 storage | $52.00 |
| **ACM** | SSL Certificate | **Free** (with ALB) | $0.00 |
| **Route53** | Hosted Zone + DNS queries | 1 zone + alias record | $0.50 |
| **S3** | Storage + Requests | ~100 GB estimate | $5.00 |
| **Secrets Manager** | 1 secret | Per-secret + API calls | $0.40 |
| **ECR** | Docker image storage | ~1 GB stored | $1.00 |
| **CloudWatch** | Dashboard + 4 alarms + logs | Metrics + alarms + ingestion | $5.00 |
| **Elastic IPs** | 2 (for NAT Gateways) | Static allocation | $7.20 |
| **Data Transfer** | Internet egress | ~50 GB/month estimate | $20.00 |
| **VPC Endpoint** | S3 Gateway Endpoint | **Free** | $0.00 |
| | | **Total** | **~$619** |

---

## 💡 Cost Optimization Strategies

### Immediate Savings (No Architecture Changes)

| Strategy | Savings | Implementation |
|:---|:---|:---|
| **Destroy dev when not in use** | Up to 100% of dev costs | `terraform destroy` after hours |
| **RDS Reserved Instance (1yr)** | ~40% on RDS | Purchase via AWS Console |
| **Fargate Savings Plans (1yr)** | ~20% on ECS | Purchase via AWS Console |
| **NAT Gateway scheduling** | ~60% of NAT cost | Stop/start NAT during business hours only |

### Architecture-Level Optimizations

| Strategy | Savings | Trade-off |
|:---|:---|:---|
| **Remove NAT Gateway (dev)** | ~$34/month | ECS tasks need VPC endpoints for ECR/Secrets instead |
| **Use Fargate Spot (dev)** | ~70% on ECS | Tasks may be interrupted with 2-min warning |
| **Single-AZ production** | ~$150/month | Reduced availability (not recommended) |
| **Smaller RDS instance** | ~$10/month | Reduced query performance |

### Free Tier Eligibility (First 12 Months)

| Service | Free Tier Allowance |
|:---|:---|
| **RDS** | 750 hours/month of db.t4g.micro |
| **S3** | 5 GB Standard storage |
| **ECR** | 500 MB storage |
| **CloudWatch** | 10 alarms, 3 dashboards |

If your AWS account is within the first 12 months, the dev environment cost drops to approximately **~$58/month** (NAT Gateway + ALB + Data Transfer).

---

## 📈 Cost Scaling Projections

As usage grows, these are the primary cost drivers:

| Growth Trigger | Impact | Estimated Additional Cost |
|:---|:---|:---|
| **+1 ECS task (auto-scale)** | More compute | +$38/month (1 vCPU / 2 GB) |
| **+100 GB S3 storage** | More files stored | +$2.30/month |
| **+1M S3 PUT requests** | High upload volume | +$5.00/month |
| **+100 GB data transfer** | More downloads | +$9.00/month |
| **RDS scale to db.t4g.medium** | More DB capacity | +$55/month |

---

## 🏷️ Cost Allocation Tags

All resources are tagged for cost tracking in AWS Cost Explorer:

```hcl
tags = {
  Environment = "dev"          # Filter by environment
  Project     = "wasktech-file-service"  # Filter by project
  Owner       = "DevOps Team"  # Filter by team
  ManagedBy   = "Terraform"    # Identify IaC-managed resources
  CostCenter  = "Engineering-Dev"  # Cost allocation
}
```

To view costs by tag in AWS Console:
1. Navigate to **AWS Billing → Cost Explorer**
2. Group by **Tag: Project** → `wasktech-file-service`
3. Filter by **Tag: Environment** → `dev`, `staging`, or `production`
