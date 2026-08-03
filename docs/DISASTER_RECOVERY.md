# 🛡️ Disaster Recovery Plan - WASK File Service Infrastructure

This document defines the Disaster Recovery (DR) strategy, RPO/RTO metrics, recovery procedures, and failover playbooks for the production Multi-Tenant File Service API.

---

## 📐 DR Objectives

| Metric | Target | Mechanism |
| :--- | :--- | :--- |
| **RPO (Recovery Point Objective)** | < 5 minutes | RDS Multi-AZ synchronous replication + Automated backups + S3 Versioning |
| **RTO (Recovery Time Objective)** | < 15 minutes | RDS automated failover (<60s) + ECS auto-healing + ALB health checks |

---

## 🏛️ Recovery Architecture

### Tier 1: Compute Recovery (ECS Fargate)

**Strategy**: Self-healing via ECS Service and ALB health checks.

- **ECS Service Controller** continuously ensures `desired_count` tasks are running.
- If a task fails its `/api/v1/health` health check (3 consecutive failures × 30s interval), ALB deregisters the target and ECS replaces the task automatically within ~60 seconds.
- **Deployment Circuit Breaker** with `rollback = true` prevents bad deployments from taking down the service.

**Recovery Action**: None required. Fully automated.

---

### Tier 2: Database Recovery (RDS PostgreSQL)

**Strategy**: Multi-AZ synchronous physical replication with automated failover.

#### Automated Failover (Production)
- RDS Multi-AZ maintains a synchronous standby replica in a separate Availability Zone.
- If the primary AZ fails, AWS automatically promotes the standby to primary within **~60 seconds**.
- No data loss (synchronous replication, RPO = 0 for AZ failures).

#### Point-in-Time Recovery (PITR)
- Automated backups retained for **35 days** (production) / **7 days** (dev/staging).
- Continuous transaction log backups allow recovery to **any second** within the retention window.

**Recovery Procedure**:
```bash
# Restore RDS to a specific point in time
aws rds restore-db-instance-to-point-in-time \
    --source-db-instance-identifier wasktech-file-service-production-db \
    --target-db-instance-identifier wasktech-file-service-production-db-restored \
    --restore-time "2026-08-03T17:00:00Z" \
    --db-instance-class db.r6g.large \
    --multi-az \
    --region us-east-1

# After verification, update Secrets Manager DATABASE_URL to point to new endpoint
aws secretsmanager update-secret \
    --secret-id wasktech-file-service/production/app-secrets \
    --secret-string '{"DATABASE_URL":"postgresql://fileapi:<password>@<new-endpoint>:5432/filedb", ...}'

# Force ECS redeployment to pick up new DATABASE_URL
aws ecs update-service \
    --cluster wasktech-file-service-production-cluster \
    --service wasktech-file-service-production-service \
    --force-new-deployment
```

#### Manual Snapshot Recovery
```bash
# Create manual snapshot before any risky operations
aws rds create-db-snapshot \
    --db-instance-identifier wasktech-file-service-production-db \
    --db-snapshot-identifier manual-pre-migration-$(date +%Y%m%d%H%M)

# Restore from manual snapshot
aws rds restore-db-instance-from-db-snapshot \
    --db-instance-identifier wasktech-file-service-production-db-from-snapshot \
    --db-snapshot-identifier manual-pre-migration-20260803
```

---

### Tier 3: Object Storage Recovery (S3)

**Strategy**: S3 Versioning + Lifecycle Policies.

- **Versioning** is enabled on the file storage bucket. Deleted or overwritten objects retain prior versions.
- **Non-current version expiration** removes old versions after 90 days (configurable).
- **S3 bucket policy** enforces TLS/SSL for all operations.

**Recovery Procedure (Accidental Object Deletion)**:
```bash
# List object versions (including delete markers)
aws s3api list-object-versions \
    --bucket wasktech-file-service-storage-production-<ACCOUNT_ID> \
    --prefix "app_id/file_uuid-filename" \
    --max-items 5

# Restore a specific previous version
aws s3api copy-object \
    --bucket wasktech-file-service-storage-production-<ACCOUNT_ID> \
    --copy-source wasktech-file-service-storage-production-<ACCOUNT_ID>/app_id/file_uuid-filename?versionId=<VERSION_ID> \
    --key app_id/file_uuid-filename
```

---

### Tier 4: Secrets Recovery (Secrets Manager)

- AWS Secrets Manager secrets are encrypted with KMS and versioned internally.
- Recovery window set to 0 days (immediate deletion) for clean reprovisioning via Terraform.
- If secrets are accidentally deleted, re-run `terraform apply` to regenerate new secrets and force ECS redeployment.

---

### Tier 5: Infrastructure Recovery (Terraform)

- **All infrastructure is codified in Terraform**. Complete infrastructure can be re-provisioned from scratch using `terraform apply`.
- Remote state stored in S3 with DynamoDB locking provides state durability and consistency.

**Full Stack Recovery Procedure**:
```bash
cd terraform/environments/production
terraform init
terraform plan -out=recovery.tfplan
terraform apply recovery.tfplan
```

---

## 🔄 Cross-Region DR (Future Enhancement)

For organizations requiring cross-region disaster recovery:

1. **S3 Cross-Region Replication (CRR)**: Replicate file storage bucket to `us-west-2`.
2. **RDS Read Replica**: Create cross-region read replica in `us-west-2`, promote on disaster.
3. **Route53 Health Checks**: Configure failover routing policy to redirect traffic to secondary region.
4. **Multi-Region ECR Replication**: Enable ECR replication rules to secondary region.

---

## 📋 DR Test Schedule

| Test | Frequency | Procedure |
| :--- | :--- | :--- |
| **RDS Failover Test** | Quarterly | `aws rds reboot-db-instance --db-instance-identifier <id> --force-failover` |
| **ECS Task Kill Test** | Monthly | Stop running tasks and verify auto-recovery |
| **PITR Restore Test** | Quarterly | Restore to point-in-time on a test instance, validate data integrity |
| **Full Terraform Recreate** | Semi-annually | Destroy and recreate dev environment from scratch |
