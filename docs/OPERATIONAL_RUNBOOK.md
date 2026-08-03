# 📖 Operational Runbook - WASK Multi-Tenant File Service API

This runbook provides step-by-step operating procedures for day-2 operations, monitoring, debugging, database management, and incident response.

---

## 📋 Table of Contents

1. [Common Day-2 Operations](#common-day-2-operations)
2. [ECS Container Debugging](#ecs-container-debugging)
3. [CloudWatch Alarm Handling](#cloudwatch-alarm-handling)
4. [Database Operations](#database-operations)
5. [Application Log Inspection](#application-log-inspection)
6. [Scaling Operations](#scaling-operations)
7. [Secret Rotation](#secret-rotation)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Validation Checklist](#validation-checklist)
10. [GitHub Secrets Configuration](#github-secrets-configuration)

---

## Common Day-2 Operations

### Force ECS Redeployment (Rolling Update)

Use this to pick up new container images or refreshed secrets:

```bash
aws ecs update-service \
    --cluster wasktech-file-service-production-cluster \
    --service wasktech-file-service-production-service \
    --force-new-deployment \
    --region us-east-1
```

### View Running ECS Tasks

```bash
aws ecs list-tasks \
    --cluster wasktech-file-service-production-cluster \
    --service-name wasktech-file-service-production-service \
    --region us-east-1
```

### Describe a Specific Task

```bash
aws ecs describe-tasks \
    --cluster wasktech-file-service-production-cluster \
    --tasks <TASK_ARN> \
    --region us-east-1
```

---

## ECS Container Debugging

### ECS Exec (Interactive Shell into Running Container)

ECS Exec is enabled in the service configuration. Use it to connect to a live container for diagnostics:

```bash
aws ecs execute-command \
    --cluster wasktech-file-service-production-cluster \
    --task <TASK_ID> \
    --container api \
    --command "/bin/sh" \
    --interactive \
    --region us-east-1
```

> **Note**: Requires `session-manager-plugin` installed locally. Install via: `curl "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/ubuntu_64bit/session-manager-plugin.deb" -o "session-manager-plugin.deb" && sudo dpkg -i session-manager-plugin.deb`

### Test Health Endpoint from Inside Container

```bash
# Inside the container after ECS Exec:
python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/api/v1/health').read().decode())"
```

### Check Environment Variables Inside Container

```bash
# Inside the container:
env | grep -E "DATABASE_URL|S3_BUCKET|ENVIRONMENT|AWS_REGION"
```

---

## CloudWatch Alarm Handling

### Alarm: `ecs-high-cpu`

**Meaning**: Average ECS CPU utilization exceeded 80% over 2 evaluation periods (10 minutes).

**Response**:
1. Check if auto scaling has triggered scale-out: `aws application-autoscaling describe-scaling-activities --service-namespace ecs`
2. Verify running task count: `aws ecs describe-services --cluster <cluster> --services <service> --query "services[0].runningCount"`
3. If scaling is insufficient, manually set higher `max_capacity` and re-apply Terraform.
4. Investigate application for CPU-intensive operations (inefficient queries, missing indexes, tight loops).

### Alarm: `ecs-high-memory`

**Meaning**: Average ECS Memory utilization exceeded 80%.

**Response**:
1. Check for memory leaks using CloudWatch Container Insights.
2. Consider increasing task memory allocation in `terraform.tfvars` and redeploying.
3. Examine logs for large payload processing or unbounded collection growth.

### Alarm: `alb-high-5xx`

**Meaning**: More than 10 HTTP 5XX errors returned by targets within 5 minutes.

**Response**:
1. Check ECS task health: `aws ecs describe-services --cluster <cluster> --services <service>`
2. Inspect application logs: `aws logs tail /ecs/wasktech-file-service-production --follow`
3. Verify RDS connectivity - if database is down, containers may return 500s.
4. Check recent deployments - if a bad deploy caused this, the circuit breaker should auto-rollback.

### Alarm: `rds-low-storage`

**Meaning**: RDS free storage has dropped below 5 GB.

**Response**:
1. Check current storage: `aws rds describe-db-instances --db-instance-identifier <id> --query "DBInstances[0].{Allocated:AllocatedStorage,Free:FreeStorageSpace}"`
2. Storage autoscaling should handle this automatically (max 100 GB configured).
3. If hitting max storage, increase `max_allocated_storage` in Terraform and apply.
4. Investigate large tables: Connect via ECS Exec and run `SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) FROM pg_catalog.pg_statio_user_tables ORDER BY pg_total_relation_size(relid) DESC LIMIT 10;`

---

## Database Operations

### Connect to RDS via ECS Exec

Since RDS is in a private subnet with no direct access, use ECS Exec to tunnel:

```bash
# 1. Shell into a running container
aws ecs execute-command --cluster <cluster> --task <task_id> --container api --command "/bin/sh" --interactive

# 2. Inside the container, install psql if needed and connect
python -c "import os; print(os.environ.get('DATABASE_URL'))"
# Use the printed DATABASE_URL to connect
```

### Run Database Migrations

If the application uses Alembic or manual SQL migrations:

```bash
# Via ECS Exec inside the container:
alembic upgrade head

# Or execute raw SQL:
python -c "
from app.db.session import engine
from sqlalchemy import text
with engine.connect() as conn:
    conn.execute(text('ALTER TABLE files ADD COLUMN IF NOT EXISTS new_col VARCHAR(255)'))
    conn.commit()
"
```

### Create Manual Database Snapshot

```bash
aws rds create-db-snapshot \
    --db-instance-identifier wasktech-file-service-production-db \
    --db-snapshot-identifier pre-migration-$(date +%Y%m%d-%H%M) \
    --region us-east-1
```

---

## Application Log Inspection

### Stream Live ECS Logs

```bash
aws logs tail /ecs/wasktech-file-service-production --follow --since 5m
```

### Search Logs for Errors

```bash
aws logs filter-log-events \
    --log-group-name /ecs/wasktech-file-service-production \
    --filter-pattern "ERROR" \
    --start-time $(date -d '1 hour ago' +%s000) \
    --region us-east-1
```

### Search for Specific Request ID

```bash
aws logs filter-log-events \
    --log-group-name /ecs/wasktech-file-service-production \
    --filter-pattern "request_id=<UUID>" \
    --region us-east-1
```

### View ALB Access Logs

ALB access logs are stored in the S3 logs bucket:

```bash
aws s3 ls s3://wasktech-file-service-logs-production-<ACCOUNT_ID>/alb-access-logs/ --recursive
aws s3 cp s3://wasktech-file-service-logs-production-<ACCOUNT_ID>/alb-access-logs/<path>/<file>.gz - | gzip -d | head -50
```

---

## Scaling Operations

### Manual Scale-Out

```bash
aws ecs update-service \
    --cluster wasktech-file-service-production-cluster \
    --service wasktech-file-service-production-service \
    --desired-count 5 \
    --region us-east-1
```

### View Auto Scaling Activities

```bash
aws application-autoscaling describe-scaling-activities \
    --service-namespace ecs \
    --resource-id service/wasktech-file-service-production-cluster/wasktech-file-service-production-service \
    --region us-east-1
```

### Modify Auto Scaling Limits

Update `ecs_min_capacity` and `ecs_max_capacity` in `terraform/environments/production/terraform.tfvars` and run:

```bash
cd terraform/environments/production
terraform plan -out=scaling.tfplan
terraform apply scaling.tfplan
```

---

## Secret Rotation

### Rotate Database Password

```bash
# 1. Generate new password
NEW_PASSWORD=$(openssl rand -base64 24)

# 2. Update RDS password
aws rds modify-db-instance \
    --db-instance-identifier wasktech-file-service-production-db \
    --master-user-password "$NEW_PASSWORD" \
    --apply-immediately

# 3. Update Secrets Manager with new DATABASE_URL
# (Use Terraform or AWS CLI to update the secret)

# 4. Force ECS redeployment to pick up new secrets
aws ecs update-service \
    --cluster wasktech-file-service-production-cluster \
    --service wasktech-file-service-production-service \
    --force-new-deployment
```

---

## Troubleshooting Guide

### Problem: ECS Tasks Fail to Start (Crash Loop)

**Diagnosis**:
```bash
# Check stopped task reasons
aws ecs describe-tasks --cluster <cluster> --tasks <stopped_task_arn> --query "tasks[0].stoppedReason"

# Check container exit code
aws ecs describe-tasks --cluster <cluster> --tasks <stopped_task_arn> --query "tasks[0].containers[0].{exitCode:exitCode,reason:reason}"
```

**Common Causes**:
- `exitCode: 1`: Application crash. Check CloudWatch logs for Python traceback.
- `exitCode: 137`: Out of Memory. Increase task memory allocation.
- `ResourceNotFoundException`: Secrets Manager secret not found. Verify ARN matches.
- `CannotPullContainerError`: ECR image not found or IAM permissions missing.

### Problem: 502 Bad Gateway from ALB

**Diagnosis**: ALB cannot reach any healthy targets.
1. Verify tasks are running: `aws ecs describe-services --cluster <cluster> --services <service>`
2. Check Target Group health: `aws elbv2 describe-target-health --target-group-arn <tg_arn>`
3. If all targets are unhealthy, the `/api/v1/health` endpoint is failing. Check application logs.

### Problem: RDS Connection Timeout

**Diagnosis**:
1. Verify RDS instance status: `aws rds describe-db-instances --db-instance-identifier <id> --query "DBInstances[0].DBInstanceStatus"`
2. Verify security group rules allow ECS → RDS on port 5432.
3. Verify `DATABASE_URL` in Secrets Manager has the correct RDS endpoint.

### Problem: S3 Presigned URL Returns AccessDenied

**Diagnosis**:
1. Verify ECS Task Role has S3 permissions: `aws iam get-role-policy --role-name <task_role> --policy-name <policy>`
2. Verify S3 bucket policy doesn't block the operation.
3. Verify KMS key grants for `kms:GenerateDataKey` and `kms:Decrypt`.
4. Check if the presigned URL has expired (default 300s).

---

## Validation Checklist

Use this checklist after every deployment or infrastructure change:

| # | Check | Command | Expected |
| :--- | :--- | :--- | :--- |
| 1 | Health endpoint responds | `curl http://<ALB_DNS>/api/v1/health` | HTTP 200 |
| 2 | HTTPS redirect works | `curl -I http://<DOMAIN>` | HTTP 301 → HTTPS |
| 3 | ECS tasks running | `aws ecs describe-services ...` | `runningCount >= desiredCount` |
| 4 | RDS instance available | `aws rds describe-db-instances ...` | `Status: available` |
| 5 | S3 bucket accessible | `aws s3 ls s3://<bucket>/` | No access denied |
| 6 | CloudWatch logs streaming | `aws logs tail /ecs/<env>` | Recent log entries visible |
| 7 | CloudWatch alarms in OK | `aws cloudwatch describe-alarms ...` | All alarms in `OK` state |
| 8 | Secrets Manager accessible | `aws secretsmanager get-secret-value --secret-id <arn>` | Returns secret JSON |
| 9 | ECR image present | `aws ecr describe-images --repository-name <repo>` | Latest image listed |
| 10 | DNS resolves (if domain) | `nslookup api.wasktech.com` | Points to ALB |

---

## GitHub Secrets Configuration

Configure the following secrets in your GitHub repository (`Settings → Secrets and variables → Actions`):

| Secret Name | Description | Example Value |
| :--- | :--- | :--- |
| `AWS_ACCESS_KEY_ID` | IAM Access Key for CI/CD deployment | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | IAM Secret Access Key | `wJal...` |
| `AWS_ACCOUNT_ID` | AWS Account Number | `123456789012` |
| `AWS_REGION` | Target AWS Region | `us-east-1` |

> **Best Practice**: Instead of using long-lived IAM Access Keys, configure [GitHub OIDC with AWS IAM Roles](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services) for keyless authentication.
