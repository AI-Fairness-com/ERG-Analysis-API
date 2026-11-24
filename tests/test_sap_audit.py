"""T-SAP-01 to 03: SAP hash in the Layer 4 audit (Chapter 16 §16.2; T4-A K2)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))
from sap_audit import REGISTERED_SAP_SHA256, sap_audit_record  # noqa: E402


def test_T_SAP_01_repository_sap_matches_registered_hash():
    rec = sap_audit_record()
    assert rec["status"] == "MATCH"
    assert rec["computed_sha256"] == REGISTERED_SAP_SHA256


def test_T_SAP_02_changed_file_is_reported_as_mismatch(tmp_path):
    changed = tmp_path / "ERG_SAP_v2.3.pdf"
    changed.write_bytes(b"not the registered plan")
    assert sap_audit_record(str(changed))["status"] == "MISMATCH"


def test_T_SAP_03_missing_file_is_reported_as_missing(tmp_path):
    rec = sap_audit_record(str(tmp_path / "absent.pdf"))
    assert rec["status"] == "MISSING" and rec["computed_sha256"] is None


def test_T_SAP_04_server_module_loads():
    """Catches a broken erg_server.py before it reaches a deploy."""
    import erg_server
    assert erg_server.app is not None
