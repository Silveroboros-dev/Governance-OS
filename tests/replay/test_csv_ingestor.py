"""
Tests for CSV Ingestor - Signal ingestion with provenance tracking.
"""

import pytest
from datetime import datetime
from pathlib import Path

from replay.csv_ingestor import (
    CSVIngestor,
    ColumnMapping,
    IngestedSignal,
    ImportBatch,
)


class TestColumnMapping:
    """Tests for ColumnMapping configuration."""

    def test_default_column_mapping(self):
        """Test default column names."""
        mapping = ColumnMapping(signal_type="type")
        assert mapping.signal_type == "type"
        assert mapping.timestamp == "timestamp"
        assert mapping.source == "source"
        assert mapping.payload_columns == {}

    def test_custom_column_mapping(self):
        """Test custom column name configuration."""
        mapping = ColumnMapping(
            signal_type="event_type",
            timestamp="event_time",
            source="origin",
            payload_columns={
                "amount": "value_usd",
                "asset": "ticker",
            },
        )
        assert mapping.signal_type == "event_type"
        assert mapping.timestamp == "event_time"
        assert mapping.payload_columns["amount"] == "value_usd"


class TestIngestedSignal:
    """Tests for IngestedSignal model."""

    def test_signal_creation(self, sample_signal_data):
        """Test creating an ingested signal."""
        signal = IngestedSignal(
            signal_type=sample_signal_data["signal_type"],
            source=sample_signal_data["source"],
            payload=sample_signal_data["payload"],
            timestamp=sample_signal_data["timestamp"],
            reliability=sample_signal_data["reliability"],
        )
        assert signal.signal_type == "position_limit_breach"
        assert signal.source == "test_system"
        assert signal.payload["asset"] == "BTC"
        assert signal.reliability == 0.95
        assert signal.id is not None  # Auto-generated

    def test_signal_with_provenance(self):
        """Test signal with provenance metadata."""
        signal = IngestedSignal(
            signal_type="test",
            source="test",
            payload={},
            timestamp=datetime.utcnow(),
            provenance={
                "source_file": "/path/to/file.csv",
                "row_number": 5,
                "batch_id": "batch_123",
            },
        )
        assert signal.provenance["source_file"] == "/path/to/file.csv"
        assert signal.provenance["row_number"] == 5


class TestCSVIngestor:
    """Tests for CSVIngestor class."""

    def test_ingestor_initialization(self):
        """Test ingestor initialization."""
        ingestor = CSVIngestor(pack="treasury")
        assert ingestor.pack == "treasury"

    def test_parse_timestamp_formats(self):
        """Test parsing various timestamp formats."""
        ingestor = CSVIngestor()

        # Standard formats
        assert ingestor._parse_timestamp("2025-01-15 10:00:00") == datetime(2025, 1, 15, 10, 0, 0)
        assert ingestor._parse_timestamp("2025-01-15T10:00:00") == datetime(2025, 1, 15, 10, 0, 0)
        assert ingestor._parse_timestamp("2025-01-15") == datetime(2025, 1, 15)

        # US format
        assert ingestor._parse_timestamp("01/15/2025") == datetime(2025, 1, 15)

    def test_parse_timestamp_invalid(self):
        """Test parsing invalid timestamp raises error."""
        ingestor = CSVIngestor()

        with pytest.raises(ValueError, match="Unable to parse timestamp"):
            ingestor._parse_timestamp("not-a-date")

    def test_parse_value_types(self):
        """Test parsing different value types from strings."""
        ingestor = CSVIngestor()

        # Integer
        assert ingestor._parse_value("123") == 123

        # Float
        assert ingestor._parse_value("123.45") == 123.45

        # Boolean
        assert ingestor._parse_value("true") is True
        assert ingestor._parse_value("false") is False

        # String
        assert ingestor._parse_value("hello") == "hello"

        # Empty/None
        assert ingestor._parse_value("") is None
        assert ingestor._parse_value("   ") is None

    def test_ingest_csv_file(self, sample_csv_file):
        """Test ingesting a CSV file."""
        ingestor = CSVIngestor(pack="treasury")
        mapping = ColumnMapping(
            signal_type="signal_type",
            timestamp="timestamp",
            source="source",
            payload_columns={
                "asset": "asset",
                "current_position": "current_position",
                "limit": "limit",
            },
        )

        batch = ingestor.ingest(sample_csv_file, mapping)

        assert isinstance(batch, ImportBatch)
        assert batch.row_count == 3
        assert len(batch.signals) == 3
        assert batch.file_hash is not None
        assert batch.source_file == str(sample_csv_file.absolute())

    def test_ingest_provenance_tracking(self, sample_csv_file):
        """Test that provenance is properly tracked."""
        ingestor = CSVIngestor()
        mapping = ColumnMapping(signal_type="signal_type")

        batch = ingestor.ingest(sample_csv_file, mapping)

        for i, signal in enumerate(batch.signals):
            assert signal.provenance["batch_id"] == batch.batch_id
            assert signal.provenance["row_number"] == i + 2  # Starts at 2 (after header)
            assert signal.provenance["file_hash"] == batch.file_hash

    def test_ingest_file_not_found(self):
        """Test error when file doesn't exist."""
        ingestor = CSVIngestor()
        mapping = ColumnMapping(signal_type="type")

        with pytest.raises(FileNotFoundError):
            ingestor.ingest(Path("/nonexistent/file.csv"), mapping)

    def test_ingest_skip_errors(self, tmp_path):
        """Test skipping rows with parse errors."""
        csv_content = """signal_type,timestamp,value
valid,2025-01-15,100
invalid,not-a-date,200
valid,2025-01-16,300
"""
        csv_path = tmp_path / "errors.csv"
        csv_path.write_text(csv_content)

        ingestor = CSVIngestor()
        mapping = ColumnMapping(signal_type="signal_type")

        # Without skip_errors, should raise
        with pytest.raises(ValueError):
            ingestor.ingest(csv_path, mapping, skip_errors=False)

        # With skip_errors, should continue
        batch = ingestor.ingest(csv_path, mapping, skip_errors=True)
        assert batch.row_count == 2  # Only valid rows

    def test_file_hash_consistency(self, sample_csv_file):
        """Test that file hash is consistent for same file."""
        ingestor = CSVIngestor()

        hash1 = ingestor._compute_file_hash(sample_csv_file)
        hash2 = ingestor._compute_file_hash(sample_csv_file)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length

    def test_extra_columns_included(self, tmp_path):
        """Test that unmapped columns are included in payload."""
        csv_content = """signal_type,timestamp,extra_field,another_field
test,2025-01-15,extra_value,123
"""
        csv_path = tmp_path / "extra.csv"
        csv_path.write_text(csv_content)

        ingestor = CSVIngestor()
        mapping = ColumnMapping(signal_type="signal_type")

        batch = ingestor.ingest(csv_path, mapping)
        signal = batch.signals[0]

        assert signal.payload["extra_field"] == "extra_value"
        assert signal.payload["another_field"] == 123
