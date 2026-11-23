"""SAP integrity record for the Layer 4 audit log (book Chapter 16 §16.2).

The registered Statistical Analysis Plan (docs/ERG_SAP_v2.2.pdf) is hashed
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

SAP_FILENAME = "ERG_SAP_v2.2.pdf"
REGISTERED_SAP_SHA256 = (
    "2c15a8a91ef05950437fe78eccc3db167639b4da6c460c6e13204000a8d0e6bd"
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
