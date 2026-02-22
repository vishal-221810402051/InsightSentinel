"""
Import all models here so:
- SQLAlchemy registers them on Base.metadata
- Alembic autogenerate can discover tables
"""

from app.models.dataset import Dataset  # noqa: F401
from app.models.dataset_column import DatasetColumn  # noqa: F401
from app.models.ingestion_run import IngestionRun  # noqa: F401
from app.models.column_statistics import ColumnStatistics  # noqa: F401
from app.models.dataset_preview import DatasetPreview  # noqa: F401