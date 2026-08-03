# 💰 AWS Monthly Cost Estimation - WASK File Service Infrastructure

This document provides estimated monthly AWS costs for each environment tier. Costs are based on **US-East-1 (N. Virginia)** pricing as of August 2026 and represent on-demand pricing without Savings Plans or Reserved Instances.

---

## 📊 Dev Environment (Minimal Footprint)

| AWS Service | Configuration | Est. Monthly Cost |
| :--- | :--- | ---: |
| **VPC / Networking** | 1 NAT Gateway + 1 Elastic IP | $35.00 |
| **Application Load Balancer** | 1 ALB (low traffic) | $18.00 |
| **ECS Fargate** | 1 Task × 0.5 vCPU × 1 GB RAM | $18.00 |
| **Amazon RDS PostgreSQL** | db.t4g.micro, Single-AZ, 20 GB gp3 | $15.00 |
| **Amazon S3** | 10 GB storage, low request volume | $2.00 |
| **AWS KMS** | 3 keys (S3, RDS, Secrets) | $3.00 |
| **Amazon ECR** | < 5 GB image storage | $0.50 |
| **CloudWatch** | Logs (5 GB), Dashboard, 4 Alarms | $8.00 |
| **Secrets Manager** | 1 secret, low retrieval | $0.50 |
| **Data Transfer** | Minimal (< 5 GB outbound) | $1.00 |
| | **Total Dev Estimate** | **~$101/mo** |

---

## 📊 Staging Environment (Moderate Footprint)

| AWS Service | Configuration | Est. Monthly Cost |
| :--- | :--- | ---: |
| **VPC / Networking** | 1 NAT Gateway + 1 Elastic IP | $35.00 |
| **Application Load Balancer** | 1 ALB (moderate traffic) | $22.00 |
| **ECS Fargate** | 2 Tasks × 0.5 vCPU × 1 GB RAM | $36.00 |
| **Amazon RDS PostgreSQL** | db.t4g.small, Single-AZ, 20 GB gp3 | $30.00 |
| **Amazon S3** | 50 GB storage, moderate requests | $5.00 |
| **AWS KMS** | 3 keys | $3.00 |
| **Amazon ECR** | < 10 GB image storage | $1.00 |
| **CloudWatch** | Logs (10 GB), Dashboard, 4 Alarms | $12.00 |
| **Secrets Manager** | 1 secret | $0.50 |
| **Data Transfer** | ~10 GB outbound | $1.00 |
| | **Total Staging Estimate** | **~$146/mo** |

---

## 📊 Production Environment (Full HA Footprint)

| AWS Service | Configuration | Est. Monthly Cost |
| :--- | :--- | ---: |
| **VPC / Networking** | 2 NAT Gateways + 2 Elastic IPs | $70.00 |
| **Application Load Balancer** | 1 ALB (production traffic) | $30.00 |
| **ECS Fargate** | 2–10 Tasks × 1 vCPU × 2 GB RAM (avg 3) | $108.00 |
| **Amazon RDS PostgreSQL** | db.r6g.large, Multi-AZ, 20–100 GB gp3 | $340.00 |
| **Amazon S3** | 500 GB storage, high request volume, IT | $18.00 |
| **AWS KMS** | 3 keys (higher API call volume) | $5.00 |
| **Amazon ECR** | < 15 GB image storage | $1.50 |
| **CloudWatch** | Logs (30 GB), Dashboard, 4 Alarms, Insights | $35.00 |
| **Secrets Manager** | 1 secret, higher retrieval | $1.00 |
| **Route53** | Hosted Zone + DNS queries | $1.50 |
| **ACM** | Free SSL Certificate | $0.00 |
| **Data Transfer** | ~100 GB outbound | $9.00 |
| | **Total Production Estimate** | **~$619/mo** |

---

## 📉 Cost Optimization Recommendations

### Immediate Savings

| Strategy | Savings | Impact |
| :--- | :--- | :--- |
| **S3 VPC Gateway Endpoint** | Already implemented | Eliminates NAT data charges for S3 traffic |
| **ECS Fargate Spot (Dev/Staging)** | Up to 70% on compute | Risk of 2-minute interruption notices |
| **RDS Reserved Instance (1yr)** | ~35-40% | Commit to 1-year db.r6g.large reservation |
| **S3 Intelligent-Tiering** | Already implemented | Auto-tiering infrequently accessed objects |
| **Single NAT Gateway (Dev)** | Already implemented | Saves ~$35/mo per removed NAT Gateway |

### Future Savings at Scale

| Strategy | When | Savings |
| :--- | :--- | :--- |
| **Savings Plans (Compute)** | After 3 months usage data | 20-40% on Fargate compute |
| **S3 Glacier Archival** | When compliance allows old files | 90%+ for archived objects |
| **Aurora Serverless v2** | If DB has variable workloads | Pay-per-query scaling |

---

## 📋 Monthly Grand Total Summary

| Environment | Est. Monthly Cost |
| :--- | ---: |
| **Development** | ~$101 |
| **Staging** | ~$146 |
| **Production** | ~$619 |
| **Total (All Environments)** | **~$866/mo** |

> **Note**: These estimates are approximate and will vary based on actual traffic volume, data storage growth, data transfer patterns, and auto scaling activity. Use **AWS Cost Explorer** and **AWS Budgets** to set alerts on spending thresholds.
