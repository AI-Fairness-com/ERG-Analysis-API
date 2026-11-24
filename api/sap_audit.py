"""SAP integrity record for the Layer 4 audit log (book Chapter 16 §16.2).

The registered Statistical Analysis Plan (docs/ERG_SAP_v2.3.pdf) is hashed
with SHA-256 and compared with the hash registered on OSF
(10.17605/OSF.IO/6WA42, Wiki Home page). The result is written to the
Layer 4 technical audit of every report, so each report shows which plan
was in force and whether the file was unchanged.

Kept in its own module so that the files locked for Phase A
(api/erg_v2_5_0.py and the normative file) are not changed.
"""
import datetime
import hashlib
import os

SAP_FILENAME = "ERG_SAP_v2.3.pdf"
REGISTERED_SAP_SHA256 = (
    "7be7f46d00d4ff42e3ae8fb1902b0c198cde55d92da1e6bc42a499a682f72bd5"
)
_DEFAULT_SAP_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "docs", SAP_FILENAME)


def sap_audit_record(sap_path: str = _DEFAULT_SAP_PATH,
                     registered_hash: str = REGISTERED_SAP_SHA256) -> dict:
    """Return the SAP integrity entry for the Layer 4 audit.

    status is MATCH, MISMATCH or MISSING. A MISMATCH or MISSING entry
    means no validation result may be reported from this run.
    """
    record = {
        "sap_file": SAP_FILENAME,
        "registered_sha256": registered_hash,
        "computed_sha256": None,
        "status": "MISSING",
        "checked_at": datetime.datetime.now(datetime.timezone.utc)
                      .isoformat(timespec="seconds"),
    }
    try:
        with open(sap_path, "rb") as f:
            computed = hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return record
    record["computed_sha256"] = computed
    record["status"] = "MATCH" if computed == registered_hash else "MISMATCH"
    return record
