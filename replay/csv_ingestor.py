"""
CSV Ingestor - Import historical signals with provenance tracking.

Converts CSV files into Signal objects with full provenance metadata
for replay and audit purposes.
"""

import csv
import hashlib
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ColumnMapping(BaseModel):
    """Maps CSV columns to signal fields."""

    signal_type: str = Field(..., description="Column name for signal type")
    timestamp: str = Field(default="timestamp", description="Column name for timestamp")
    source: str = Field(default="source", description="Column name for source")
    payload_columns: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of payload field names to CSV column names"
    )
    reliability: Optional[str] = Field(default=None, description="Column for reliability score")


def compute_signal_content_hash(
    pack: str,
    signal_type: str,
    payload: dict,
    source: str,
    observed_at: datetime
) -> str:
    """Compute deterministic content hash for signal deduplication."""
    observed_str = observed_at.isoformat() if isinstance(observed_at, datetime) else str(observed_at)
    content = {
        "pack": pack,
        "signal_type": signal_type,
        "payload": payload,
        "source": source,
        "observed_at": observed_str
    }
    import json
    canonical = json.dumps(content, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


class IngestedSignal(BaseModel):
    """Signal with provenance metadata from CSV import."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    signal_type: str
    source: str
    payload: Dict[str, Any]
    timestamp: datetime
    reliability: float = 1.0

    # Provenance metadata
    provenance: Dict[str, Any] = Field(default_factory=dict)

    # Idempotency
    content_hash: Optional[str] = None


class ImportBatch(BaseModel):
    """Represents a batch of imported signals."""

    batch_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_file: str
    import_timestamp: datetime = Field(default_factory=datetime.utcnow)
    row_count: int
    signals: List[IngestedSignal]
    file_hash: str
    column_mapping: ColumnMapping
    parse_errors: List[Dict[str, Any]] = Field(default_factory=list)

    # Deduplication stats (populated by ingest_to_db)
    signals_created: int = 0
    signals_deduplicated: int = 0


class CSVIngestor:
    """
    Ingests CSV files into signals with full provenance tracking.

    Provenance includes:
    - Source file path and hash
    - Row number in original file
    - Import batch ID
    - Import timestamp
    - Column mapping used
    """

    def __init__(self, pack: str = "treasury"):
        """
        Initialize the ingestor.

        Args:
            pack: Domain pack name for signal type validation
        """
        self.pack = pack

    def _compute_file_hash(self, filepath: Path) -> str:
        """Compute SHA256 hash of the file for provenance."""
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _parse_timestamp(self, value: str) -> datetime:
        """Parse timestamp from various formats."""
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(value.strip(), fmt)
            except ValueError:
                continue

        raise ValueError(f"Unable to parse timestamp: {value}")

    def _parse_value(self, value: str) -> Any:
        """Parse string value to appropriate type."""
        if not value or value.strip() == "":
            return None

        value = value.strip()

        # Try boolean
        if value.lower() in ("true", "false"):
            return value.lower() == "true"

        # Try integer
        try:
            return int(value)
        except ValueError:
            pass

        # Try float
        try:
            return float(value)
        except ValueError:
            pass

        return value

    def ingest(
        self,
        filepath: Path,
        column_mapping: ColumnMapping,
        skip_errors: bool = False
    ) -> ImportBatch:
        """
        Ingest a CSV file into signals with provenance.

        Args:
            filepath: Path to the CSV file
            column_mapping: Mapping of CSV columns to signal fields
            skip_errors: If True, skip rows with parsing errors

        Returns:
            ImportBatch containing all ingested signals with provenance
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"CSV file not found: {filepath}")

        file_hash = self._compute_file_hash(filepath)
        batch_id = str(uuid.uuid4())
        signals: List[IngestedSignal] = []
        errors: List[Dict[str, Any]] = []

        with open(filepath, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                try:
                    signal = self._parse_row(
                        row=row,
                        column_mapping=column_mapping,
                        filepath=filepath,
                        row_num=row_num,
                        batch_id=batch_id,
                        file_hash=file_hash
                    )
                    signals.append(signal)
                except Exception as e:
                    if skip_errors:
                        errors.append({
                            "row": row_num,
                            "error": str(e),
                            "data": row
                        })
                    else:
                        raise ValueError(f"Error parsing row {row_num}: {e}") from e

        batch = ImportBatch(
            batch_id=batch_id,
            source_file=str(filepath.absolute()),
            row_count=len(signals),
            signals=signals,
            file_hash=file_hash,
            column_mapping=column_mapping
        )

        if errors:
            batch.parse_errors = errors

        return batch

    def _parse_row(
        self,
        row: Dict[str, str],
        column_mapping: ColumnMapping,
        filepath: Path,
        row_num: int,
        batch_id: str,
        file_hash: str
    ) -> IngestedSignal:
        """Parse a single CSV row into a signal."""

        # Extract signal type
        signal_type = row.get(column_mapping.signal_type, "").strip()
        if not signal_type:
            raise ValueError(f"Missing signal type in column '{column_mapping.signal_type}'")

        # Extract timestamp
        timestamp_str = row.get(column_mapping.timestamp, "").strip()
        if not timestamp_str:
            timestamp = datetime.utcnow()
        else:
            timestamp = self._parse_timestamp(timestamp_str)

        # Extract source
        source = row.get(column_mapping.source, "csv_import").strip() or "csv_import"

        # Extract reliability if configured
        reliability = 1.0
        if column_mapping.reliability and column_mapping.reliability in row:
            try:
                reliability = float(row[column_mapping.reliability])
            except (ValueError, TypeError):
                reliability = 1.0

        # Build payload from configured columns
        payload: Dict[str, Any] = {}
        for field_name, column_name in column_mapping.payload_columns.items():
            if column_name in row:
                payload[field_name] = self._parse_value(row[column_name])

        # Also include any extra columns not explicitly mapped
        mapped_columns = {
            column_mapping.signal_type,
            column_mapping.timestamp,
            column_mapping.source,
            column_mapping.reliability,
            *column_mapping.payload_columns.values()
        }
        for col_name, col_value in row.items():
            if col_name not in mapped_columns and col_value:
                payload[col_name] = self._parse_value(col_value)

        # Build provenance metadata
        provenance = {
            "source_file": str(filepath.absolute()),
            "file_hash": file_hash,
            "row_number": row_num,
            "batch_id": batch_id,
            "import_timestamp": datetime.utcnow().isoformat(),
            "column_mapping": column_mapping.model_dump()
        }

        return IngestedSignal(
            signal_type=signal_type,
            source=source,
            payload=payload,
            timestamp=timestamp,
            reliability=reliability,
            provenance=provenance
        )

    def ingest_to_db(
        self,
        filepath: Path,
        column_mapping: ColumnMapping,
        db_session,
        skip_errors: bool = False,
        skip_duplicates: bool = True
    ) -> ImportBatch:
        """
        Ingest CSV and persist signals to database (idempotent).

        Args:
            filepath: Path to the CSV file
            column_mapping: Mapping of CSV columns to signal fields
            db_session: SQLAlchemy database session
            skip_errors: If True, skip rows with parsing errors
            skip_duplicates: If True, skip signals that already exist (default: True)

        Returns:
            ImportBatch with database-persisted signals and deduplication stats
        """
        from core.models import Signal as DBSignal
        from core.models.signal import SignalReliability

        batch = self.ingest(filepath, column_mapping, skip_errors)

        created_count = 0
        dedupe_count = 0

        # Map reliability float to enum
        def get_reliability_enum(rel_float: float) -> SignalReliability:
            if rel_float >= 0.9:
                return SignalReliability.HIGH
            elif rel_float >= 0.7:
                return SignalReliability.MEDIUM
            elif rel_float >= 0.5:
                return SignalReliability.LOW
            else:
                return SignalReliability.UNVERIFIED

        for signal in batch.signals:
            # Compute content hash for idempotency
            content_hash = compute_signal_content_hash(
                pack=self.pack,
                signal_type=signal.signal_type,
                payload=signal.payload,
                source=signal.source,
                observed_at=signal.timestamp
            )
            signal.content_hash = content_hash

            # Check for existing signal (idempotency)
            existing = db_session.query(DBSignal).filter(
                DBSignal.content_hash == content_hash
            ).first()

            if existing:
                dedupe_count += 1
                if skip_duplicates:
                    continue
                else:
                    raise ValueError(
                        f"Duplicate signal detected: {signal.signal_type} at {signal.timestamp}"
                    )

            # Create new signal
            db_signal = DBSignal(
                id=uuid.UUID(signal.id),
                pack=self.pack,
                signal_type=signal.signal_type,
                source=signal.source,
                payload=signal.payload,
                observed_at=signal.timestamp,
                reliability=get_reliability_enum(signal.reliability),
                signal_metadata=signal.provenance,
                content_hash=content_hash
            )
            db_session.add(db_signal)
            created_count += 1

        db_session.commit()

        # Update batch stats
        batch.signals_created = created_count
        batch.signals_deduplicated = dedupe_count

        return batch
