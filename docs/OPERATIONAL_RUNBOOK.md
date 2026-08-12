# 📖 Operational Runbook — WASK Multi-Tenant File Service API

This runbook provides step-by-step procedures for day-2 operations, monitoring, debugging, incident response, database management, and common troubleshooting scenarios.

---

## 📋 Table of Contents

1. [Service Endpoints & Access](#-service-endpoints--access)
2. [Health Monitoring](#-health-monitoring)
3. [ECS Operations](#-ecs-operations)
4. [Database Operations](#-database-operations)
5. [S3 Storage Operations](#-s3-storage-operations)
6. [Secrets Management](#-secrets-management)
7. [Incident Response Playbooks](#-incident-response-playbooks)
8. [CloudWatch Alarms Reference](#-cloudwatch-alarms-reference)
9. [Log Analysis](#-log-analysis)
10. [Cost Monitoring](#-cost-monitoring)

---

## 🌐 Service Endpoints & Access

### Environment URLs

| Environment | API Endpoint | CloudWatch Dashboard |
|:---|:---|:---|
| **Dev** | `http://<dev-alb-dns>/api/v1` | `wasktech-file-service-dev-dashboard` |
| **Staging** | `http://<staging-alb-dns>/api/v1` | `wasktech-file-service-staging-dashboard` |
| **Production** | `http://<prod-alb-dns>/api/v1` | `wasktech-file-service-production-dashboard` |

### Key Resource Names (Dev)

```
ECS Cluster:   wasktech-file-service-dev-cluster
ECS Service:   wasktech-file-service-dev-service
ALB:           wasktech-file-service-dev-alb
RDS Instance:  wasktech-file-service-dev-db
ECR Repo:      wasktech-file-service-api-dev
S3 Bucket:     wasktech-file-service-storage-dev-<account-id>
Secret:        wasktech-file-service/dev/app-secrets
```

---

## 🩺 Health Monitoring

### Quick Health Check

```bash
# Check API health
curl -s http://<ALB_DNS>/api/v1/health | jq .

# Expected response:
# {"status": "healthy", "service": "File Service API"}
```

### ECS Service Status

```bash
# Check running tasks
aws ecs describe-services \
    --cluster wasktech-file-service-dev-cluster \
    --services wasktech-file-service-dev-service \
    --query "services[0].{Status:status,Running:runningCount,Desired:desiredCount,Pending:pendingCount}" \
    --output table

# List individual tasks
aws ecs list-tasks \
    --cluster wasktech-file-service-dev-cluster \
    --service-name wasktech-file-service-dev-service \
    --output table
```

### ALB Target Health

```bash
# Get Target Group ARN
TG_ARN=$(aws elbv2 describe-target-groups \
    --names wasktech-file-service-dev-tg \
    --query "TargetGroups[0].TargetGroupArn" \
    --output text)

# Check target health
aws elbv2 describe-target-health \
    --target-group-arn $TG_ARN \
    --output table
```

### RDS Instance Status

```bash
aws rds describe-db-instances \
    --db-instance-identifier wasktech-file-service-dev-db \
    --query "DBInstances[0].{Status:DBInstanceStatus,Engine:Engine,Version:EngineVersion,Class:DBInstanceClass,Storage:AllocatedStorage,MultiAZ:MultiAZ}" \
    --output table
```

---

## 🐳 ECS Operations

### Force a New Deployment (Rolling Update)

```bash
aws ecs update-service \
    --cluster wasktech-file-service-dev-cluster \
    --service wasktech-file-service-dev-service \
    --force-new-deployment \
    --region us-east-1
```

### Scale ECS Tasks Manually

```bash
# Scale to 3 tasks
aws ecs update-service \
    --cluster wasktech-file-service-dev-cluster \
    --service wasktech-file-service-dev-service \
    --desired-count 3

# Scale back to 1
aws ecs update-service \
    --cluster wasktech-file-service-dev-cluster \
    --service wasktech-file-service-dev-service \
    --desired-count 1
```

### View Running Task Details

```bash
# Get task ARN
TASK_ARN=$(aws ecs list-tasks \
    --cluster wasktech-file-service-dev-cluster \
    --service-name wasktech-file-service-dev-service \
    --query "taskArns[0]" --output text)

# Describe task (including container status, health, network)
aws ecs describe-tasks \
    --cluster wasktech-file-service-dev-cluster \
    --tasks $TASK_ARN \
    --query "tasks[0].{Status:lastStatus,Health:healthStatus,CPU:cpu,Memory:memory,StartedAt:startedAt}" \
    --output table
```

### Stop a Specific Task (Force Restart)

```bash
aws ecs stop-task \
    --cluster wasktech-file-service-dev-cluster \
    --task $TASK_ARN \
    --reason "Manual restart for debugging"
```

ECS will automatically start a replacement task.

### View ECS Task Definition

```bash
aws ecs describe-task-definition \
    --task-definition wasktech-file-service-dev-task \
    --query "taskDefinition.{Family:family,CPU:cpu,Memory:memory,Image:containerDefinitions[0].image}" \
    --output table
```

---

## 🗄️ Database Operations

### Connect to RDS via ECS Exec (Production-Safe)

For direct database access, use ECS Exec to open a shell inside the running container:

```bash
# Enable ECS Exec on the service (one-time)
aws ecs update-service \
    --cluster wasktech-file-service-dev-cluster \
    --service wasktech-file-service-dev-service \
    --enable-execute-command

# Get task ARN
TASK_ARN=$(aws ecs list-tasks \
    --cluster wasktech-file-service-dev-cluster \
    --query "taskArns[0]" --output text)

# Open interactive shell
aws ecs execute-command \
    --cluster wasktech-file-service-dev-cluster \
    --task $TASK_ARN \
    --container api \
    --interactive \
    --command "/bin/sh"

# Once inside the container, connect to PostgreSQL:
# python -c "from app.core.config import get_settings; print(get_settings().DATABASE_URL)"
```

### Application Seeding & API Key Rotation in AWS ECS

Because the production RDS PostgreSQL database resides inside a private VPC subnet (inaccessible directly from local developer workstations), seeding consuming applications or rotating API keys for deployed environments must be executed as a one-off Fargate task in ECS.

#### Method 1: AWS CLI (One-Off Task Execution)

1. Create a temporary overrides file `overrides.json`:
```json
{
  "containerOverrides": [
    {
      "name": "api",
      "command": ["python", "seed_app.py", "el_roi_pay_file_server", "El Roi Pay File Server", "--rotate"]
    }
  ]
}
```
*(Omit `--rotate` when seeding a new application for the first time).*

2. Launch the task in the ECS cluster:
```bash
aws ecs run-task \
    --cluster wasktech-file-service-dev-cluster \
    --task-definition wasktech-file-service-dev-task \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-0a16005f7d5f013b6],securityGroups=[sg-015e633bf1c3f1da7],assignPublicIp=ENABLED}" \
    --overrides file://overrides.json \
    --query "tasks[0].taskArn" --output text
```

3. Retrieve the generated API key from CloudWatch logs:
```bash
aws logs get-log-events \
    --log-group-name "/ecs/wasktech-file-service-dev" \
    --log-stream-name "api/api/<task-id>" \
    --query "events[*].message" --output text
```

#### Method 2: AWS Web Console

1. Navigate to **AWS Console** $\rightarrow$ **Elastic Container Service (ECS)** $\rightarrow$ **Clusters** $\rightarrow$ `wasktech-file-service-dev-cluster`.
2. Under the **Tasks** tab, click **Run new task**.
3. Select **Fargate** launch type and task definition `wasktech-file-service-dev-task`.
4. Under **Container Overrides**:
   - Container Name: `api`
   - Command Override: `python,seed_app.py,el_roi_pay_file_server,El Roi Pay File Server,--rotate`
5. Click **Run Task**, wait for execution to complete (Status: `STOPPED`), then view the **Logs** tab to retrieve the new API Key.

### Common Database Queries

```sql
-- Count active files by tenant
SELECT app_id, COUNT(*) as file_count, 
       SUM(size) as total_bytes
FROM files 
WHERE deleted_at IS NULL 
GROUP BY app_id;

-- List registered tenants
SELECT id, name, created_at FROM apps ORDER BY created_at;

-- Find failed uploads (stuck in PENDING > 1 hour)
SELECT uuid, original_filename, app_id, created_at 
FROM files 
WHERE status = 'PENDING' 
  AND created_at < NOW() - INTERVAL '1 hour'
  AND deleted_at IS NULL;

-- Storage usage by month
SELECT DATE_TRUNC('month', created_at) as month,
       COUNT(*) as files_uploaded,
       SUM(size) as total_bytes
FROM files 
WHERE deleted_at IS NULL 
GROUP BY month 
ORDER BY month DESC;
```

### RDS Backup & Restore

```bash
# Create manual snapshot
aws rds create-db-snapshot \
    --db-instance-identifier wasktech-file-service-dev-db \
    --db-snapshot-identifier manual-backup-$(date +%Y%m%d)

# List available snapshots
aws rds describe-db-snapshots \
    --db-instance-identifier wasktech-file-service-dev-db \
    --query "DBSnapshots[*].{ID:DBSnapshotIdentifier,Status:Status,Created:SnapshotCreateTime}" \
    --output table

# Point-in-Time Recovery (restore to a new instance)
aws rds restore-db-instance-to-point-in-time \
    --source-db-instance-identifier wasktech-file-service-dev-db \
    --target-db-instance-identifier wasktech-file-service-dev-db-restored \
    --restore-time "2026-08-04T12:00:00Z"
```

---

## 📦 S3 Storage Operations

### Check Bucket Contents

```bash
# Count objects by tenant (app_id prefix)
aws s3 ls s3://wasktech-file-service-storage-dev-<ACCOUNT_ID>/ --recursive --summarize

# List files for a specific tenant
aws s3 ls s3://wasktech-file-service-storage-dev-<ACCOUNT_ID>/main_app/
```

### Recover Deleted Files (Versioning Enabled)

```bash
# List all versions including delete markers
aws s3api list-object-versions \
    --bucket wasktech-file-service-storage-dev-<ACCOUNT_ID> \
    --prefix "main_app/" \
    --max-items 20

# Restore by deleting the delete marker
aws s3api delete-object \
    --bucket wasktech-file-service-storage-dev-<ACCOUNT_ID> \
    --key "main_app/file-uuid-filename.pdf" \
    --version-id "<DELETE_MARKER_VERSION_ID>"
```

### Check Bucket Storage Size

```bash
aws cloudwatch get-metric-statistics \
    --namespace AWS/S3 \
    --metric-name BucketSizeBytes \
    --dimensions Name=BucketName,Value=wasktech-file-service-storage-dev-<ACCOUNT_ID> Name=StorageType,Value=StandardStorage \
    --start-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 86400 \
    --statistics Average \
    --output table
```

---

## 🔑 Secrets Management

### View Current Secret Keys (Not Values)

```bash
aws secretsmanager describe-secret \
    --secret-id "wasktech-file-service/dev/app-secrets" \
    --output table
```

### Rotate Database Password

```bash
# 1. Generate new password
NEW_PASSWORD=$(openssl rand -base64 24)

# 2. Update in Secrets Manager
aws secretsmanager put-secret-value \
    --secret-id "wasktech-file-service/dev/app-secrets" \
    --secret-string "{\"DATABASE_URL\":\"postgresql://fileapi:${NEW_PASSWORD}@<RDS_ENDPOINT>:5432/filedb\",\"POSTGRES_USER\":\"fileapi\",\"POSTGRES_PASSWORD\":\"${NEW_PASSWORD}\",\"POSTGRES_DB\":\"filedb\"}"

# 3. Update RDS master password
aws rds modify-db-instance \
    --db-instance-identifier wasktech-file-service-dev-db \
    --master-user-password "$NEW_PASSWORD" \
    --apply-immediately

# 4. Force ECS to re-pull secrets
aws ecs update-service \
    --cluster wasktech-file-service-dev-cluster \
    --service wasktech-file-service-dev-service \
    --force-new-deployment
```

---

## 🚨 Incident Response Playbooks

### Playbook 1: ECS Tasks Crashing (0 Running Tasks)

**Symptoms**: API returns 502/503, no healthy targets in ALB

```bash
# 1. Check service events for error messages
aws ecs describe-services \
    --cluster wasktech-file-service-dev-cluster \
    --services wasktech-file-service-dev-service \
    --query "services[0].events[:5]" \
    --output table

# 2. Check the stopped task reason
TASK_ARN=$(aws ecs list-tasks \
    --cluster wasktech-file-service-dev-cluster \
    --desired-status STOPPED \
    --query "taskArns[0]" --output text)

aws ecs describe-tasks \
    --cluster wasktech-file-service-dev-cluster \
    --tasks $TASK_ARN \
    --query "tasks[0].{StopCode:stopCode,StopReason:stoppedReason,Container:containers[0].{Status:lastStatus,Reason:reason,ExitCode:exitCode}}"

# 3. Common causes:
#    - Container image not found → Check ECR repo has an image tagged :latest
#    - Secrets access denied → Check IAM execution role has secretsmanager:GetSecretValue
#    - OOM killed → Increase memory in terraform.tfvars
#    - Database connection refused → Check RDS is running and security groups allow 5432
```

### Playbook 2: High 5XX Error Rate

**Symptoms**: CloudWatch alarm `alb-high-5xx` triggered

```bash
# 1. Check ALB target health
aws elbv2 describe-target-health \
    --target-group-arn <TG_ARN> --output table

# 2. Check ECS task health
aws ecs describe-services \
    --cluster wasktech-file-service-dev-cluster \
    --services wasktech-file-service-dev-service \
    --query "services[0].{Running:runningCount,Desired:desiredCount}"

# 3. If tasks are healthy but 5XX persist, check application logs
# (See Log Analysis section below)

# 4. If caused by a bad deployment, roll back:
# Identify the previous task definition revision
aws ecs list-task-definitions \
    --family-prefix wasktech-file-service-dev-task \
    --sort DESC --max-items 5

# Deploy the previous revision
aws ecs update-service \
    --cluster wasktech-file-service-dev-cluster \
    --service wasktech-file-service-dev-service \
    --task-definition wasktech-file-service-dev-task:<PREVIOUS_REVISION>
```

### Playbook 3: RDS Storage Running Low

**Symptoms**: CloudWatch alarm `rds-low-storage` triggered

```bash
# 1. Check current storage usage
aws rds describe-db-instances \
    --db-instance-identifier wasktech-file-service-dev-db \
    --query "DBInstances[0].{Allocated:AllocatedStorage,FreeStorage:FreeStorageSpace}"

# 2. Clean up stale PENDING records (orphaned upload sessions)
# Connect to DB and run:
# DELETE FROM files WHERE status = 'PENDING' AND created_at < NOW() - INTERVAL '7 days';

# 3. If storage consistently low, increase via Terraform:
# Edit terraform.tfvars: allocated_storage = 50
# terraform plan && terraform apply
```

### Playbook 4: Database Connection Failures

**Symptoms**: API returns 500, logs show "connection refused" or "timeout"

```bash
# 1. Check RDS instance status
aws rds describe-db-instances \
    --db-instance-identifier wasktech-file-service-dev-db \
    --query "DBInstances[0].DBInstanceStatus"

# 2. Verify security group allows ECS → RDS traffic
aws ec2 describe-security-groups \
    --group-ids <RDS_SG_ID> \
    --query "SecurityGroups[0].IpPermissions"

# 3. If RDS is in "storage-full" state, see Playbook 3
# If RDS is "modifying", wait for the operation to complete
# If RDS is "failed", restore from snapshot (see Database Operations)
```

---

## 📊 CloudWatch Alarms Reference

| Alarm Name | Metric | Threshold | Period | Description |
|:---|:---|:---|:---|:---|
| `*-ecs-high-cpu` | ECS CPU Utilization | > 80% | 5 min | ECS tasks consuming excessive CPU |
| `*-ecs-high-memory` | ECS Memory Utilization | > 80% | 5 min | ECS tasks consuming excessive memory |
| `*-alb-high-5xx` | ALB Target 5XX Count | > 10 errors | 5 min | Application returning server errors |
| `*-rds-low-storage` | RDS Free Storage Space | < 2 GB | 5 min | Database storage critically low |

### View Alarm States

```bash
aws cloudwatch describe-alarms \
    --alarm-name-prefix "wasktech-file-service-dev" \
    --query "MetricAlarms[*].{Name:AlarmName,State:StateValue,Reason:StateReason}" \
    --output table
```

---

## 📝 Log Analysis

### View ECS Application Logs

```bash
# View last 100 log events
aws logs get-log-events \
    --log-group-name "/ecs/wasktech-file-service-dev" \
    --log-stream-name "api/<TASK_ID>" \
    --limit 100

# Search logs for errors (requires CloudWatch Logs Insights access)
aws logs filter-log-events \
    --log-group-name "/ecs/wasktech-file-service-dev" \
    --filter-pattern "ERROR" \
    --limit 50
```

### Find the Log Stream Name

```bash
aws logs describe-log-streams \
    --log-group-name "/ecs/wasktech-file-service-dev" \
    --order-by LastEventTime \
    --descending \
    --limit 5 \
    --query "logStreams[*].{StreamName:logStreamName,LastEvent:lastEventTimestamp}" \
    --output table
```

---

## 💰 Cost Monitoring

### Monthly Cost Breakdown by Service

| Service | Dev/Month | Production/Month |
|:---|:---|:---|
| **NAT Gateway** | ~$34 | ~$68 |
| **ALB** | ~$18 | ~$18 |
| **ECS Fargate** | ~$19 | ~$75 |
| **RDS PostgreSQL** | ~$13 | ~$52 |
| **S3 Storage** | ~$1 | ~$5 |
| **Secrets Manager** | ~$1 | ~$1 |
| **CloudWatch** | ~$3 | ~$5 |
| **ECR** | ~$1 | ~$1 |
| **Data Transfer** | ~$5 | ~$20 |
| **Total Estimate** | **~$101** | **~$619** |

### Cost Optimization Tips

1. **Dev/Staging**: Use `terraform destroy` when not actively testing
2. **NAT Gateway**: Largest dev cost — the S3 VPC Endpoint already saves money on file operations
3. **RDS**: Use `db.t4g.micro` for dev (free tier eligible for first 12 months)
4. **ECS**: Single task in dev is sufficient; production auto-scales as needed
