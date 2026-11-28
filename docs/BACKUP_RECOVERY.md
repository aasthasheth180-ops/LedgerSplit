# LedgerSplit — Backup and Recovery

## 1. Backup Strategy

LedgerSplit uses PostgreSQL custom-format backups through `pg_dump`.

Backups include database records, schemas, indexes, sequences, primary keys, foreign keys and uniqueness constraints.

## 2. Automated Backups

The reusable backup script is located at `scripts/backup.ps1`.

Run manually:

```powershell
.\scripts\backup.ps1
```

The script performs timestamped backup creation, archive readability validation, SHA256 checksum generation, retention cleanup and temporary container file removal.

## 3. Storage and Retention

Backups are stored outside the Git repository at:

`%LOCALAPPDATA%\LedgerSplit\backups`

- Retention period: seven days.
- Access: Windows account, SYSTEM and administrators.
- Schedule: daily at 3 AM.
- Scheduled task: LedgerSplitDailyBackup.
- Expired backup deletion: tested successfully.
- Scheduled execution: tested successfully.

Docker Desktop and the database container must be available for scheduled execution.

## 4. Recovery Procedure

Select the desired backup and verify its SHA256 checksum against the corresponding checksum file, where available.

Copy the backup into the database container:

```powershell
docker compose --env-file .env.docker cp "$backupFile" db:/tmp/recovery.dump
```

Create a separate recovery database:

```powershell
docker compose --env-file .env.docker exec -T db createdb -U ledger ledger_recovery
```

Stop if the database already exists or creation fails.

Restore the archive:

```powershell
docker compose --env-file .env.docker exec -T db pg_restore -U ledger -d ledger_recovery --exit-on-error --single-transaction /tmp/recovery.dump
```

Verify restored records before considering any production recovery or database replacement.

## 5. Recovery Test Results

Test date: November 28, 2026.

| Metric | Result |
|---|---|
| PostgreSQL version | 18.7 |
| Tables backed up | 13 |
| Initial backup size | 48,044 bytes |
| Archive entries | 121 |
| Initial measured restore duration | 1.709 seconds |
| Restoration errors | 0 |
| Initial core table fingerprint comparisons | 7/7 matched |
| Confirmed payment recovery | Passed |
| Retention deletion test | Passed |
| Scheduled backup execution | Passed |

The initial recovery test verified users, groups, group memberships, expenses, expense splits, payments and payment requests using record counts and content fingerprints.

A subsequent recovery test successfully restored a nonempty payment table containing one confirmed payment.

## 6. Financial Data Integrity

Recovery verification includes:

- User and group records.
- Group memberships.
- Expense records and splits.
- Payment records and confirmation status.
- Payment requests.
- Database constraints supporting referential integrity and idempotency.

## 7. Current Limitations

- Backups are stored locally and are not independently encrypted.
- Local backups do not protect against complete device loss.
- Recovery testing uses separate databases within the same PostgreSQL instance.
- Scheduled execution depends on local infrastructure availability.
- Measured restoration time reflects a small test dataset, not a production recovery-time guarantee.
- Point-in-time recovery and off-device encrypted backups remain future production improvements.