import sqlite3
import datetime
from pathlib import Path
from typing import Optional


def _log_backup_progress(status, remaining, total):
    """Callback function to log backup progress"""
    percent = (total - remaining) / total * 100
    print(f"Database backup progress: {percent:.1f}% complete ({remaining} pages remaining)")

def backup_database(
    source_db_path: str = "./data/expenis.db",
    backup_dir: str = "./data/backups",
    max_backups: Optional[int] = 5
) -> str:
    """
    Creates a backup of the SQLite database using the online backup API.
    Optionally rotates old backups to keep only the most recent ones.
    
    Args:
        source_db_path: Path to source database file
        backup_dir: Directory to store backups
        max_backups: Maximum number of backups to keep (None to keep all)
        
    Returns:
        Path to the created backup file
    """
    # Ensure paths are absolute and directories exist
    source_db_path = str(Path(source_db_path).absolute())
    backup_dir = Path(backup_dir).absolute()
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Create timestamped backup filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"expenis_backup_{timestamp}.db"
    
    try:
        # Connect to source and destination databases
        source_conn = sqlite3.connect(source_db_path)
        backup_conn = sqlite3.connect(str(backup_path))
        
        # Create backup with progress logging
        with backup_conn:
            source_conn.backup(backup_conn, pages=100, progress=_log_backup_progress)
            print("Database backup completed successfully")
        
        # Rotate old backups if max_backups is set
        if max_backups is not None and max_backups > 0:
            backups = sorted(backup_dir.glob("expenis_backup_*.db"))
            for old_backup in backups[:-max_backups]:
                old_backup.unlink()
                
        return str(backup_path)
        
    except sqlite3.Error as e:
        raise RuntimeError(f"Database backup failed: {e}")
    finally:
        if 'source_conn' in locals():
            source_conn.close()
        if 'backup_conn' in locals():
            backup_conn.close()

if __name__ == '__main__':
    backup_database()