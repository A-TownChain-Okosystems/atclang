"""ATCLang IR — normalisierte JSON-Zwischendarstellung (Tooling-Basis)."""
from .json_ir import to_json_ir, IRValidationError, validate_ir, ir_hash

__all__ = ["to_json_ir", "IRValidationError", "validate_ir", "ir_hash"]
