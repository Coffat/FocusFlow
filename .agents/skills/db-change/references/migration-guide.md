# Alembic Migration Guide — FocusFlow

## Migration File Structure

```python
"""add learning_plan_goals table

Revision ID: abc123
Revises: def456
Create Date: 2026-10-23 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'abc123'
down_revision: Union[str, None] = 'def456'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'learning_plan_goals',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('plan_id', sa.String(36), sa.ForeignKey('learning_plans.id'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('target_date', sa.Date, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_learning_plan_goals_plan_id', 'learning_plan_goals', ['plan_id'])
    op.create_foreign_key(
        'fk_learning_plan_goals_learning_plans',
        'learning_plan_goals', 'learning_plans',
        ['plan_id'], ['id'],
        ondelete='CASCADE',
    )


def downgrade() -> None:
    op.drop_constraint('fk_learning_plan_goals_learning_plans', 'learning_plan_goals', type_='foreignkey')
    op.drop_index('ix_learning_plan_goals_plan_id', table_name='learning_plan_goals')
    op.drop_table('learning_plan_goals')
```

## ORM Model Pattern (SQLAlchemy 2.0)

```python
# infrastructure/database/orm/learning_plan_orm.py
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.infrastructure.database.base import Base

class LearningPlanORM(Base):
    __tablename__ = "learning_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    # Relationships
    goals: Mapped[list["LearningPlanGoalORM"]] = relationship(back_populates="plan")
```

## Naming Conventions

| Object | Convention | Example |
|--------|-----------|---------|
| Table | `snake_case`, plural | `learning_plans` |
| Column | `snake_case` | `created_at` |
| Foreign Key | `fk_{child}_{parent}` | `fk_learning_plan_goals_learning_plans` |
| Index | `ix_{table}_{column}` | `ix_learning_plans_user_id` |
| Unique | `uq_{table}_{column}` | `uq_users_email` |
| Check | `ck_{table}_{column}` | `ck_tasks_status` |

## Common Pitfalls

1. **Never use `pass` in `downgrade()`** — always reverse what `upgrade()` did.
2. **Never modify a committed migration** — create a new one instead.
3. **Column renames** require `op.alter_column()` with explicit `existing_type`.
4. **Data migrations** should be idempotent and handle empty tables gracefully.
5. **Always test roundtrip**: upgrade → downgrade → upgrade must succeed.
