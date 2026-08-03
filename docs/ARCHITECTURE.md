# 🏛️ Enterprise AWS Architecture - WASK Multi-Tenant File Service API

This document presents the detailed architectural design for the production platform hosting the **WASK Technologies Multi-Tenant File Service API**.

---

## 📐 System Architecture Diagram

```
                                      [ Internet Clients ]
                                               │
                                       (HTTPS Port 443)
                                               ▼
                                    [ Route53 (DNS Alias) ]
                                               │
                                               ▼
                              [ AWS Certificate Manager (SSL) ]
                                               │
                                               ▼
                            [ Application Load Balancer (ALB) ]
                         (Public Subnets across 2+ Availability Zones)
                                               │
                       ┌───────────────────────┴───────────────────────┐
                       │                                               │
               (HTTP Port 8000)                                (Access Logs)
                       │                                               │
                       ▼                                               ▼
         [ Amazon ECS Fargate Service ]                       [ S3 Access Logs Bucket ]
     (FastAPI Containers in Private Subnets)
    ┌──────────────────┴──────────────────┐
    │                                     │
    ▼                                     ▼
[ Amazon RDS PostgreSQL 16 ]     [ AWS Secrets Manager ] ──► (Injected DB Password & Secrets)
 (Multi-AZ Private DB Subnets)            │
    │                                     │
    └──────────────────┬──────────────────┘
                       │
                       ▼
             [ Amazon S3 Bucket ] ◄───────── (Direct Presigned PUT / GET from Clients)
       (KMS Encrypted, Versioned,
       Intelligent-Tiering, TLS Only)
                       │
                       ▼
            [ Amazon CloudWatch ]
       (Log Groups, Dashboard & Alarms)
```

---

## 🔒 Defense-in-Depth Security Layers

1. **Edge Security**: HTTPS termination at ALB with TLS 1.3/1.2 protocols using ACM Certificates. Mandatory HTTP (80) to HTTPS (443) redirect.
2. **Network Isolation (VPC)**:
   - Public Subnets: ALB only.
   - Private Application Subnets: ECS Fargate Tasks (no public IP addresses attached).
   - Private Database Subnets: RDS PostgreSQL 16 (completely unreachable from the Internet).
   - Gateway VPC Endpoint for S3: All traffic between ECS tasks and S3 travels entirely across AWS internal backbone network without NAT charges or Internet routing.
3. **Security Groups**:
   - `alb_sg`: Accepts 80 and 443 from `0.0.0.0/0`.
   - `ecs_sg`: Accepts 8000 strictly from `alb_sg`.
   - `rds_sg`: Accepts 5432 strictly from `ecs_sg`.
4. **Least Privilege IAM Roles**:
   - `ecs_task_execution_role`: Restricted to pulling ECR images, creating CloudWatch log streams, and reading specific Secrets Manager ARNs.
   - `ecs_task_role`: Restricted to S3 object operations (`GetObject`, `PutObject`, `DeleteObject`, `HeadObject`) on the designated file service S3 bucket.
5. **Data Encryption**:
   - **At Rest**: S3 bucket encrypted with customer-managed KMS key (`SSE-KMS`). RDS database storage and automated snapshots encrypted with KMS key. Secrets Manager secrets encrypted with KMS key.
   - **In Transit**: Mandatory TLS 1.3/1.2 (`aws:SecureTransport`) enforced by S3 bucket policies, ALB listeners, and PostgreSQL `rds.force_ssl=1` parameter.

---

## ⚡ High Availability & Resiliency Design

- **Multi-AZ Deployment**: ALB listeners span across 2+ Availability Zones (`us-east-1a`, `us-east-1b`).
- **Amazon ECS Fargate**: Deploys multi-AZ task instances with deployment circuit breakers and dynamic target-tracking auto scaling (CPU & Memory at 70%).
- **Amazon RDS PostgreSQL 16**: Multi-AZ deployment with synchronous physical replication to a secondary standby DB in a separate AZ for zero-data-loss failover (<60s RTO).
- **Auto Healing**: ALB health checks poll `/api/v1/health` every 30 seconds. Unhealthy containers are automatically terminated and replaced by ECS Fargate.
