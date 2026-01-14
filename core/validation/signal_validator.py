"""
Signal Validator - Validates signals against pack schemas.

Ensures signals match expected types and payload structures
before entering the deterministic kernel.
"""

from typing import Any, Dict, List, Optional, Tuple


class ValidationError(Exception):
    """Raised when signal validation fails."""

    def __init__(self, message: str, errors: List[Dict[str, str]] = None):
        super().__init__(message)
        self.errors = errors or []


# Type mapping from schema strings to Python type checks
TYPE_VALIDATORS = {
    "string": lambda v: isinstance(v, str),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "array": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
}


class SignalValidator:
    """Validates signals against pack-defined schemas."""

    def __init__(self):
        """Initialize validator with pack signal type definitions."""
        self._pack_schemas: Dict[str, Dict[str, Any]] = {}
        self._load_pack_schemas()

    def _load_pack_schemas(self):
        """Load signal type definitions from all packs."""
        # Import pack definitions
        try:
            from packs.treasury.signal_types import TREASURY_SIGNAL_TYPES
            self._pack_schemas["treasury"] = TREASURY_SIGNAL_TYPES
        except ImportError:
            pass

        try:
            from packs.wealth.signal_types import WEALTH_SIGNAL_TYPES
            self._pack_schemas["wealth"] = WEALTH_SIGNAL_TYPES
        except ImportError:
            pass

    def get_valid_packs(self) -> List[str]:
        """Return list of valid pack names."""
        return list(self._pack_schemas.keys())

    def get_signal_types(self, pack: str) -> List[str]:
        """Return list of valid signal types for a pack."""
        if pack not in self._pack_schemas:
            return []
        return list(self._pack_schemas[pack].keys())

    def validate(
        self,
        pack: str,
        signal_type: str,
        payload: Dict[str, Any]
    ) -> Tuple[bool, List[Dict[str, str]]]:
        """
        Validate a signal against its pack schema.

        Args:
            pack: Pack name (e.g., "treasury", "wealth")
            signal_type: Signal type (e.g., "position_limit_breach")
            payload: Signal payload data

        Returns:
            Tuple of (is_valid, errors)
            - is_valid: True if validation passed
            - errors: List of error dicts with "field" and "message" keys
        """
        errors = []

        # Validate pack exists
        if pack not in self._pack_schemas:
            errors.append({
                "field": "pack",
                "message": f"Unknown pack '{pack}'. Valid packs: {', '.join(self.get_valid_packs())}"
            })
            return False, errors

        # Validate signal_type exists in pack
        pack_types = self._pack_schemas[pack]
        if signal_type not in pack_types:
            valid_types = ", ".join(pack_types.keys())
            errors.append({
                "field": "signal_type",
                "message": f"Unknown signal_type '{signal_type}' for pack '{pack}'. Valid types: {valid_types}"
            })
            return False, errors

        # Get schema for this signal type
        signal_def = pack_types[signal_type]
        payload_schema = signal_def.get("payload_schema", {})

        # Validate payload against schema
        payload_errors = self._validate_payload(payload, payload_schema)
        errors.extend(payload_errors)

        return len(errors) == 0, errors

    def _validate_payload(
        self,
        payload: Dict[str, Any],
        schema: Dict[str, str]
    ) -> List[Dict[str, str]]:
        """
        Validate payload against schema.

        Args:
            payload: The payload data
            schema: Schema definition mapping field names to types

        Returns:
            List of validation errors
        """
        errors = []

        if not isinstance(payload, dict):
            errors.append({
                "field": "payload",
                "message": "Payload must be an object"
            })
            return errors

        # Check for required fields (all fields in schema are required)
        for field_name, field_type in schema.items():
            if field_name not in payload:
                errors.append({
                    "field": f"payload.{field_name}",
                    "message": f"Missing required field '{field_name}'"
                })
                continue

            # Validate field type
            value = payload[field_name]
            if value is None:
                errors.append({
                    "field": f"payload.{field_name}",
                    "message": f"Field '{field_name}' cannot be null"
                })
                continue

            # Get type validator
            type_validator = TYPE_VALIDATORS.get(field_type)
            if type_validator and not type_validator(value):
                errors.append({
                    "field": f"payload.{field_name}",
                    "message": f"Field '{field_name}' must be of type '{field_type}', got '{type(value).__name__}'"
                })

        return errors

    def validate_or_raise(
        self,
        pack: str,
        signal_type: str,
        payload: Dict[str, Any]
    ) -> None:
        """
        Validate a signal, raising ValidationError if invalid.

        Args:
            pack: Pack name
            signal_type: Signal type
            payload: Signal payload data

        Raises:
            ValidationError: If validation fails
        """
        is_valid, errors = self.validate(pack, signal_type, payload)
        if not is_valid:
            error_messages = [f"{e['field']}: {e['message']}" for e in errors]
            raise ValidationError(
                f"Signal validation failed: {'; '.join(error_messages)}",
                errors=errors
            )


# Singleton instance for reuse
_validator_instance: Optional[SignalValidator] = None


def get_signal_validator() -> SignalValidator:
    """Get the singleton SignalValidator instance."""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = SignalValidator()
    return _validator_instance
