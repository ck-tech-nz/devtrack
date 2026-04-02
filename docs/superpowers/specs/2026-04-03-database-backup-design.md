# Database Backup Feature Design

## Overview

Add a one-click database backup feature to DevTrack's web UI, allowing administrators to trigger PostgreSQL backups, view backup history, and download backup files. Backup files are stored on the host machine outside Docker containers via volume mount.

## Architecture

```
[Frontend UI] --POST /api/settings/backups/--> [Django async view]
                                                  |
                                        asyncio.create_subprocess_exec
                                                  |
                                        pg_dump (reads DB config from Django settings)
                                                  |
                                        writes to /data/backups/ (volume mount)
                                                  |
                                        creates DatabaseBackup record
                                                  |
[Frontend UI] <-- backup record JSON response ---
```

- `pg_dump` connects to the database using credentials from `settings.DATABASES['default']`
- In production, the backend container reaches PostgreSQL via `db-network`
- Dump files are written to `/data/backups/`, mapped to a host directory via Docker volume
- No SSH required

## Data Model

New model in `settings` app:

```python
class DatabaseBackup(models.Model):
    filename = models.CharField(max_length=255)       # devtrack_20260403_120000.dump
    file_size = models.BigIntegerField(null=True)      # bytes
    status = models.CharField(max_length=20, choices=[
        ("running", "备份中"),
        ("success", "成功"),
        ("failed", "失败"),
    ])
    error_message = models.TextField(blank=True)       # error details on failure
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
```

## API Design

Base path: `/api/settings/backups/`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/settings/backups/` | List backup records (paginated) |
| POST | `/api/settings/backups/` | Trigger new backup |
| GET | `/api/settings/backups/{id}/download/` | Download backup file |
| DELETE | `/api/settings/backups/{id}/` | Delete backup record and file |

**Access control:** All endpoints require `is_staff=True` (admin role). Not using model permissions.

### POST /api/settings/backups/ (trigger backup)

1. Create `DatabaseBackup` record with `status="running"`
2. Execute `pg_dump` via `asyncio.create_subprocess_exec`:
   ```
   pg_dump -h <DB_HOST> -p <DB_PORT> -U <DB_USER> -Fc <DB_NAME> -f /data/backups/<filename>
   ```
   - `-Fc` = custom binary format (compressed, smaller files)
   - `PGPASSWORD` passed via environment
3. On success: update record with `status="success"` and `file_size`
4. On failure: update record with `status="failed"` and `error_message`
5. Return the backup record as JSON

### GET /api/settings/backups/{id}/download/

Stream the dump file using `FileResponse`. Filename from the record, content type `application/octet-stream`.

### DELETE /api/settings/backups/{id}/

Delete both the database record and the file on disk. If file is already gone, just delete the record.

## Backend Infrastructure Changes

### a) Switch to ASGI

- Add `uvicorn` dependency
- Change production command from `runserver` to `uvicorn config.asgi:application --host 0.0.0.0 --port 8000`
- Existing `config/asgi.py` already exists

### b) Install `postgresql-client` in Dockerfile

- Add `apt-get install -y postgresql-client` to backend Dockerfile
- Required for `pg_dump` command

### c) New setting in `settings.py`

```python
BACKUP_DIR = os.environ.get("BACKUP_DIR", "/data/backups")
```

Database connection info is read directly from `DATABASES['default']`.

### d) Production docker-compose volume addition

```yaml
volumes:
  - backups:/data/backups
  - ./.gitconfig-proxy:/root/.gitconfig:ro
  - repo_data:/data/repos
```

## Frontend

### Page

- **Route:** `/app/settings/backups`
- **Access:** Admin only (route guard + nav visibility)

### UI Layout

- Top: "立即备份" button — triggers POST, shows loading state until response
- Below: Table with columns:
  - 文件名
  - 大小 (human-readable, e.g., "15.2 MB")
  - 状态 (备份中 / 成功 / 失败)
  - 操作人
  - 时间
  - 操作 (下载 / 删除)

### Permission Integration

- Add to `useNavigation.ts` nav items (admin check)
- Add to `auth.global.ts` route permissions (admin check)
