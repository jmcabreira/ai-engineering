# Data Retention Policy — DataOps Knowledge Hub
**Owner:** team-platform | **Last updated:** 2026-01 | **Compliance:** LGPD

---

## 1. Purpose

This policy defines the retention, archival, and deletion procedures for all data assets managed by the DataOps platform. Compliance is mandatory for all teams.

---

## 2. Data Classification and Retention Periods

| Classification | Examples | Retention | Storage |
|---------------|----------|-----------|---------|
| **PII** | customer name, email | 90 days after account closure | Encrypted at rest |
| **Transactional** | orders, payments, invoices | 7 years (legal requirement) | Cold storage after 1 year |
| **Operational Logs** | pipeline event_logs, user_activity | 30 days | Hot storage |
| **Analytical** | fact_revenue, dim_customers | 3 years | Data warehouse |
| **System Logs** | application logs, access logs | 90 days | Log aggregator |

---

## 3. PII Handling (LGPD Compliance)

Under Brazil's Lei Geral de Proteção de Dados (LGPD — Law 13.709/2018):

- **Customers table:** `name` and `email` fields are classified as PII.
- Data subjects may request deletion at any time via the DPO (dpo@company.com).
- Upon deletion request, PII must be purged within **15 business days**.
- Deletion cascades to: `orders` (customer_id reference), `user_activity` (user_id), analytical copies.
- A deletion log must be kept for 5 years (without the PII itself).

**Responsible team:** team-platform

---

## 4. Deletion Procedures

### Automated deletion (scheduled)
- `event_logs` older than 30 days: daily job at 02:00 UTC run by `etl_billing_daily`
- `user_activity` older than 30 days: daily cleanup job
- Soft delete first (set `deleted_at` timestamp), hard delete after 7-day grace period

### Manual deletion (upon request)
1. DPO receives deletion request → creates ticket in Jira
2. team-platform executes anonymization script on `customers` table
3. team-billing purges related `orders` PII fields
4. team-analytics removes PII from warehouse snapshots
5. DPO confirms deletion within 15 business days

---

## 5. Archival Process

Data older than retention period transitions through:
1. **Hot** (0–90 days): Operational databases (PostgreSQL, MongoDB)
2. **Warm** (90 days–1 year): Compressed replicas in SeaweedFS
3. **Cold** (1–7 years): Archived in long-term storage, read-only
4. **Deleted**: Secure wipe after maximum retention period

---

## 6. Responsibilities

| Team | Responsibility |
|------|---------------|
| team-platform | PII data, customers schema, deletion scripts |
| team-billing | Orders data, financial records (7-year retention) |
| team-analytics | Warehouse snapshots, aggregated metrics |
| Security | Encryption keys, access audit logs |
