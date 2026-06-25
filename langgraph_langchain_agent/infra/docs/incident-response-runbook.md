# Incident Response Runbook — DataOps Platform
**Owner:** team-platform | **Last updated:** 2026-01

---

## 1. Severity Classification

| Severity | Definition | Example |
|----------|------------|---------|
| **P1 — Critical** | Production data unavailable, SLA breached, revenue impact | etl_billing_daily failed, fact_revenue not updated |
| **P2 — High** | Pipeline degraded, SLA at risk, partial data loss | etl_orders_hourly running >2x normal duration |
| **P3 — Medium** | Non-critical pipeline delayed, no immediate user impact | etl_customer_sync delayed by 15 min |
| **P4 — Low** | Informational alert, no SLA risk | Warning threshold crossed, no breach |

---

## 2. Communication Channels

| Channel | Purpose |
|---------|---------|
| PagerDuty | P1/P2 on-call alerts |
| #incidents (Slack) | P1/P2 real-time coordination |
| #data-alerts (Slack) | Automated pipeline alerts |
| #billing-eng (Slack) | Billing pipeline issues |
| #platform-eng (Slack) | Infrastructure issues |
| #analytics (Slack) | Analytics pipeline issues |

---

## 3. Step-by-Step Response

### P1 — Critical Incident

1. **Alert fires** → PagerDuty notifies on-call engineer
2. **Acknowledge** within 15 min → post to #incidents: `"P1 ACTIVE: [brief description] — investigating"`
3. **Diagnose:**
   ```bash
   # Check pipeline logs
   docker compose logs data-generator --tail 50
   # Check database connectivity
   docker compose exec postgres pg_isready
   # Check Qdrant
   curl http://localhost:6333/healthz
   # Check Neo4j
   docker compose exec neo4j cypher-shell -u neo4j -p dataops123 "RETURN 1"
   ```
4. **Notify stakeholders** within 30 min: email to data-stakeholders@company.com
5. **Resolve or escalate** within SLA window
6. **Post resolution:** Update #incidents: `"P1 RESOLVED: [root cause] — [fix applied]"`
7. **Post-mortem** within 48h (see Section 5)

### P2 — High Severity

1. Alert fires → Slack #data-alerts + team channel
2. Investigate within 30 min
3. Status updates every 30 min in team channel
4. Resolve within business day

---

## 4. Rollback Procedures

### Pipeline rollback
```bash
# Stop failed pipeline container
docker compose stop data-generator

# Check last known good state
docker compose logs data-generator --tail 100

# Restart with previous image
docker compose up -d data-generator
```

### Database rollback
```bash
# PostgreSQL — restore from backup
docker compose exec postgres pg_restore -U dataops -d dataops /backups/latest.dump

# Neo4j — restore graph
docker compose exec neo4j neo4j-admin database restore --from-path=/backups/neo4j
```

### Qdrant rollback
```bash
# Delete and recreate collection from last ingestion
curl -X DELETE http://localhost:6333/collections/dataops-memory
python -m src.ingestion.run
```

---

## 5. Post-Mortem Template

```markdown
## Incident Post-Mortem

**Date:** YYYY-MM-DD
**Severity:** P1/P2
**Duration:** X hours Y minutes
**On-call:** [name]

### Timeline
- HH:MM — Alert fired
- HH:MM — Investigation started
- HH:MM — Root cause identified
- HH:MM — Fix applied
- HH:MM — Incident resolved

### Root Cause
[Describe the root cause]

### Impact
- Pipelines affected: [list]
- Data delay: [duration]
- Downstream impact: [dashboards, reports]

### Resolution
[What was done to fix it]

### Action Items
- [ ] [Preventive action 1] — Owner: [team] — Due: YYYY-MM-DD
- [ ] [Preventive action 2] — Owner: [team] — Due: YYYY-MM-DD
```
