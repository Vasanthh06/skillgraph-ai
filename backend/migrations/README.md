# Database migrations

SkillGraph creates fresh databases from the SQLAlchemy models (`python scripts/init_db.py`).
Existing databases are upgraded **in place** — no data is dropped:

```bash
python scripts/migrate_db.py
```

| Migration | What it adds |
|---|---|
| `002_skill_intelligence` | `user_skill_assessments.confidence_rating` (+ uniqueness per user/skill, duplicates merged newest-first); `user_skills` calibration/freshness/review cache columns; `interview_attempts.purpose/session_id/topic/is_correct` (+ indexes); `user_progress.completed_at` (backfilled from `updated_at`); new `skill_recall_schedules` table (unique per user/skill). |

The migration code is idempotent and works on SQLite and PostgreSQL. Run it once after pulling
this update, before starting the API against an older database.
