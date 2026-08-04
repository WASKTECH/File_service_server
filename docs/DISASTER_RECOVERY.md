# 🛡️ Disaster Recovery Plan — WASK File Service Infrastructure

This document defines the Disaster Recovery (DR) strategy, RPO/RTO targets, recovery procedures, and failover playbooks for the Multi-Tenant File Service API.

---

## 📊 RPO / RTO Targets by Environment

| Metric | Dev | Staging | Production |
|:---|:---|:---|:---|
| **RPO** (Recovery Point Objective) | 24 hours | 24 hours | 5 minutes |
| **RTO** (Recovery Time Objective) | 4 hours | 2 hours | 30 minutes |
| **Backup Strategy** | Daily snapshots | Daily snapshots | Multi-AZ + PITR |

---

## 🏗️ Built-In Resilience Features

### Amazon RDS PostgreSQL 16

| Feature | Dev/Staging | Production |
|:---|:---|:---|
| **Automated Backups** | ✅ 7-day retention | ✅ 7-day retention |
| **Point-in-Time Recovery (PITR)** | ✅ 5-min granularity | ✅ 5-min granularity |
| **Multi-AZ Standby** | ❌ | ✅ Synchronous replication |
| **Automated Failover** | ❌ | ✅ < 60 seconds |
| **Deletion Protection** | ❌ | ✅ Enabled |
| **Storage Encryption** | ✅ AWS-managed | ✅ AWS-managed |

### Amazon S3

| Feature | All Environments |
|:---|:---|
| **Durability** | 99.999999999% (11 nines) |
| **Versioning** | ✅ Enabled — accidental deletions recoverable |
| **Cross-Region Replication** | ❌ (add when needed) |
| **Lifecycle Rules** | Incomplete multipart uploads cleaned up after 7 days |
| **TLS Enforcement** | ✅ Bucket policy denies non-HTTPS |

### Amazon ECS Fargate

| Feature | All Environments |
|:---|:---|
| **Multi-AZ Task Placement** | ✅ Spread across 2 AZs |
| **Deployment Circuit Breaker** | ✅ Auto-rollback on failure |
| **Health Check Auto-Recovery** | ✅ Unhealthy tasks replaced automatically |
| **Rolling Deployment** | ✅ Zero-downtime updates |

---

## 🔄 Recovery Procedures

### Scenario 1: Single ECS Task Failure

**Impact**: Temporary capacity reduction, ALB routes to remaining healthy tasks
**Auto-Recovery**: ECS automatically replaces the failed task within 2-3 minutes
**Manual Action**: None required

```bash
# Monitor replacement progress
aws ecs describe-services \
    --cluster wasktech-file-service-dev-cluster \
    --services wasktech-file-service-dev-service \
    --query "services[0].{Running:runningCount,Desired:desiredCount,Events:events[:3]}" \
    --output json
```

### Scenario 2: Bad Deployment (Application Error)

**Impact**: All new tasks crash, API becomes unavailable
**Detection**: CloudWatch 5XX alarm triggers

```bash
# Step 1: Identify the last working task definition revision
aws ecs list-task-definitions \
    --family-prefix wasktech-file-service-dev-task \
    --sort DESC --max-items 5 --output table

# Step 2: Roll back to the previous working revision
aws ecs update-service \
    --cluster wasktech-file-service-dev-cluster \
    --service wasktech-file-service-dev-service \
    --task-definition wasktech-file-service-dev-task:<PREVIOUS_REVISION> \
    --force-new-deployment

# Step 3: Wait for stability
aws ecs wait services-stable \
    --cluster wasktech-file-service-dev-cluster \
    --services wasktech-file-service-dev-service
```

### Scenario 3: RDS Instance Failure (Single-AZ / Dev)

**Impact**: Database unavailable, API returns 500 errors
**Recovery Time**: 15-30 minutes

```bash
# Step 1: Check instance status
aws rds describe-db-instances \
    --db-instance-identifier wasktech-file-service-dev-db \
    --query "DBInstances[0].DBInstanceStatus"

# Step 2: If status is "failed", restore from the most recent automated snapshot
aws rds describe-db-snapshots \
    --db-instance-identifier wasktech-file-service-dev-db \
    --query "DBSnapshots[-1].{ID:DBSnapshotIdentifier,Time:SnapshotCreateTime}" \
    --output table

# Step 3: Restore to a new instance
aws rds restore-db-instance-from-db-snapshot \
    --db-instance-identifier wasktech-file-service-dev-db-restored \
    --db-snapshot-identifier <SNAPSHOT_ID> \
    --db-instance-class db.t4g.micro \
    --db-subnet-group-name wasktech-file-service-dev-db-subnet-group \
    --vpc-security-group-ids <RDS_SG_ID>

# Step 4: Update Secrets Manager with new endpoint
# Step 5: Force ECS redeployment to pick up new DB endpoint
```

### Scenario 4: RDS Instance Failure (Multi-AZ / Production)

**Impact**: Automatic failover to standby replica
**Recovery Time**: < 60 seconds (automatic)
**Manual Action**: None — AWS handles the failover automatically

```bash
# Monitor failover events
aws rds describe-events \
    --source-identifier wasktech-file-service-production-db \
    --source-type db-instance \
    --duration 60 \
    --output table
```

### Scenario 5: Point-in-Time Recovery (Data Corruption)

**Impact**: Application logic error corrupted data
**Use When**: You need to recover the database to a specific moment before the corruption

```bash
# Step 1: Identify the exact timestamp before corruption
# (Check application logs for the last known good state)

# Step 2: Restore to a point in time
aws rds restore-db-instance-to-point-in-time \
    --source-db-instance-identifier wasktech-file-service-dev-db \
    --target-db-instance-identifier wasktech-file-service-dev-db-pitr \
    --restore-time "2026-08-04T12:00:00Z" \
    --db-instance-class db.t4g.micro \
    --db-subnet-group-name wasktech-file-service-dev-db-subnet-group

# Step 3: Verify data integrity on the restored instance
# Step 4: Update Secrets Manager with the new endpoint
# Step 5: Rename or swap the instances
```

### Scenario 6: S3 Accidental File Deletion

**Impact**: User files deleted from storage
**Recovery**: S3 versioning preserves all previous versions

```bash
# Step 1: List deleted objects (delete markers)
aws s3api list-object-versions \
    --bucket wasktech-file-service-storage-dev-<ACCOUNT_ID> \
    --prefix "main_app/" \
    --query "DeleteMarkers[*].{Key:Key,VersionId:VersionId,DeletedAt:LastModified}"

# Step 2: Remove the delete marker to restore the file
aws s3api delete-object \
    --bucket wasktech-file-service-storage-dev-<ACCOUNT_ID> \
    --key "main_app/<file-key>" \
    --version-id "<DELETE_MARKER_VERSION_ID>"
```

### Scenario 7: Entire Region Failure (us-east-1)

**Impact**: Complete infrastructure outage
**Recovery Strategy**: Rebuild in alternate region

```bash
# Step 1: Copy latest RDS snapshot to alternate region
aws rds copy-db-snapshot \
    --source-db-snapshot-identifier <SNAPSHOT_ARN> \
    --target-db-snapshot-identifier dr-snapshot-$(date +%Y%m%d) \
    --source-region us-east-1 \
    --region us-west-2

# Step 2: Deploy infrastructure in us-west-2
cd terraform/environments/production
# Update terraform.tfvars: aws_region = "us-west-2"
terraform init && terraform plan -out=tfplan && terraform apply tfplan

# Step 3: Restore RDS from copied snapshot
# Step 4: Rebuild ECR and push Docker image
# Step 5: Update DNS to point to new ALB
```

---

## 📋 DR Testing Schedule

| Test Type | Frequency | Procedure |
|:---|:---|:---|
| **RDS Snapshot Restore** | Monthly | Restore latest snapshot to a test instance, verify data |
| **ECS Task Kill Test** | Weekly | Stop a running task, verify auto-recovery |
| **Deployment Rollback** | Per release | Deploy a known-bad image, verify circuit breaker triggers |
| **PITR Recovery Test** | Quarterly | Restore to a random timestamp, verify data consistency |
| **Full DR Simulation** | Semi-annually | Deploy entire stack in alternate region from snapshots |

---

## 🔐 Backup Inventory

| Resource | Backup Method | Retention | Location |
|:---|:---|:---|:---|
| **RDS Database** | Automated snapshots | 7 days | Same region |
| **RDS Database** | Manual snapshots | Indefinite | Same region |
| **S3 Files** | Versioning | Indefinite | Same bucket |
| **Terraform State** | Local file (dev) | Manual backup | `terraform.tfstate` |
| **Secrets Manager** | AWS-managed | Version history | Same region |
| **ECR Images** | Lifecycle policy | Last 10 images | Same region |
| **Application Code** | Git | Full history | GitHub |

---

## ⚠️ Recovery Decision Matrix

| Failure Type | Automatic? | RTO | Data Loss? | Action |
|:---|:---|:---|:---|:---|
| Single task crash | ✅ Auto | 2-3 min | None | Monitor only |
| Bad deployment | ✅ Circuit breaker | 5 min | None | Verify rollback |
| AZ failure | ✅ Multi-AZ | 1-5 min | None | Monitor |
| RDS failure (prod) | ✅ Multi-AZ failover | < 60 sec | None | Monitor |
| RDS failure (dev) | ❌ Manual | 15-30 min | Up to RPO | Restore snapshot |
| Data corruption | ❌ Manual | 30-60 min | To PITR point | PITR recovery |
| S3 deletion | ❌ Manual | 5 min | None (versioned) | Remove delete marker |
| Region failure | ❌ Manual | 2-4 hours | Up to RPO | Cross-region rebuild |
