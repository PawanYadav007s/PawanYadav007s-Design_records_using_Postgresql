import os
import subprocess
from datetime import datetime

# === CONFIGURATION ===
DB_USERNAME='designappuser'
DB_PASSWORD='DesignPass123'
DB_HOST='localhost'
DB_PORT='5432'
DB_NAME='design_db'
BACKUP_DIR = os.path.expanduser('~/db_backups')  # or use any path
RETENTION_DAYS = 7
os.makedirs(BACKUP_DIR, exist_ok=True)

os.makedirs(BACKUP_DIR, exist_ok=True)

# === Generate backup filename ===
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
filename = f"{DB_NAME}_backup_{timestamp}.sql"
filepath = os.path.join(BACKUP_DIR, filename)

# === Perform the backup using pg_dump ===
try:
    subprocess.run([
        'pg_dump',
        '-U', DB_USERNAME,
        '-h', DB_HOST,
        '-p', DB_PORT,
        '-F', 'c',  # Custom format (compressed)
        '-f', filepath,
        DB_NAME
    ], check=True, env={**os.environ, "PGPASSWORD": DB_PASSWORD})
    print(f"✅ Backup created: {filepath}")
except subprocess.CalledProcessError as e:
    print(f"❌ Backup failed: {e}")

# === Cleanup old backups ===
now = datetime.now().timestamp()
for file in os.listdir(BACKUP_DIR):
    path = os.path.join(BACKUP_DIR, file)
    if os.path.isfile(path) and path.endswith('.sql'):
        modified_time = os.path.getmtime(path)
        if modified_time < now - (RETENTION_DAYS * 86400):
            os.remove(path)
            print(f"🗑️ Deleted old backup: {file}")