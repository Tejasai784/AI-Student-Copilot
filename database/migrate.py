import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import inspect, text
from database.database import Base, engine, init_db
from database.models import (
    User, RefreshToken, StudentProfile, Subject, Document,
    StudyPlan, ExamAttempt, StudentSettings
)

def run_migration():
    print("Step 1: Initializing missing tables...")
    init_db()

    insp = inspect(engine)
    with engine.connect() as conn:
        print("Step 2: Checking and adding missing columns...")
        tables_to_check = {
            'users': [
                ('hashed_password', 'VARCHAR(255)'),
                ('updated_at', 'DATETIME')
            ],
            'student_profiles': [
                ('user_id', 'INTEGER')
            ],
            'subjects': [
                ('user_id', 'INTEGER')
            ],
            'documents': [
                ('user_id', 'INTEGER')
            ],
            'student_settings': [
                ('user_id', 'INTEGER')
            ],
            'exam_attempts': [
                ('user_id', 'INTEGER')
            ],
            'study_plans': [
                ('user_id', 'INTEGER')
            ]
        }
        
        for table_name, cols in tables_to_check.items():
            existing_cols = {c['name'] for c in insp.get_columns(table_name)}
            for col_name, col_type in cols:
                if col_name not in existing_cols:
                    print(f"  Adding column {col_name} to {table_name}...")
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}"))
                    conn.commit()

        print("Step 3: Checking default user...")
        user = conn.execute(text("SELECT id FROM users WHERE id = 1")).first()
        if not user:
            print("  Creating default local_student user (id=1)...")
            conn.execute(text(
                "INSERT INTO users (id, username, email, full_name, role, is_active, created_at, updated_at) "
                "VALUES (1, 'local_student', 'student@example.com', 'Student', 'student', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ))
            conn.commit()

        print("Step 4: Backfilling user_id = 1 for existing records...")
        for t in ['student_profiles', 'subjects', 'documents', 'student_settings', 'exam_attempts', 'study_plans']:
            conn.execute(text(f"UPDATE {t} SET user_id = 1 WHERE user_id IS NULL"))
            conn.commit()

    print("Migration completed successfully!")

if __name__ == "__main__":
    run_migration()
