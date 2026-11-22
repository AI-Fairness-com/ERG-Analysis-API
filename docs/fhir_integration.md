# HL7 FHIR R4 Output of the ERG Analysis API

This page describes the FHIR output that the API returns with every analysis. It follows Appendix B of *Hands-On Electroretinography in the Age of AI* and the class `ERGFHIRGenerator` in `api/erg_v2_5_0.py`.

FHIR (Fast Healthcare Interoperability Resources) is the HL7 International standard for exchanging health records between computer systems. Measured values use LOINC codes wherever a code exists. Values without a LOINC code use the project's own codes and extensions, whose addresses begin with `https://ai-fairness.com/fhir/erg/`.

No classifier has been trained yet. The FHIR output therefore carries the measured values, the Traffic Light zone against the normative reference, and the audit record, but no disease classification.

## What the API returns

Each call to `POST /api/v1/analyse` analyzes one recording: one protocol in one eye. The JSON response contains:

| Key | Content |
|---|---|
| `fhir_observation` | One Observation for the recording (Appendix B §B.1) |
| `fhir_bundle` | A Bundle of type `collection` holding that Observation, a DiagnosticReport, and an AuditEvent (Appendix B §B.3) |

## Observation

| Element | Value |
|---|---|
| `code` | LOINC **79894-2**, Electroretinography (ERG) panel |
| `status` | `final` for a recording that passes the quality checks or carries a Warning |
| `subject` | `Patient/[patient_id]`, a de-identified code |
| `effectiveDateTime` | Recording date, date only |
| `bodySite.text` | `Right eye (OD)` or `Left eye (OS)` |
| `performer` | `Organization/[center_id]`, when known |
| `device` | `Device/[device_manufacturer]`, when known |
| `extension` | `iscev-protocol`, `electrode-type`, and `version-stamp` (four parts: `api_version`, `model_weights_hash`, `config_hash`, `normative_ref_version`) |
| `component` | One per measured value, coded as in the table below |
| `note` | A Warning caveat, a corrected signal polarity, or an atypical PhNR, when they apply |

The eye is taken from the form field `eye` (`OD` or `OS`) or, if that is empty, from the `eye` column of the uploaded CSV (Appendix A). `model_weights_hash` is `PENDING` until a trained model is deployed.

## Component codes (Appendix B, Table B.1)

| Feature | Protocols | Right eye (OD) | Left eye (OS) | Unit |
|---|---|---|---|---|
| `a_amp_uv` | DA 3.0, DA 10.0 | 79773-8 | 79774-6 | uV |
| `a_implicit_ms` | DA 3.0, DA 10.0 | 79777-9 | 79778-7 | ms |
| `b_amp_uv` | DA 0.01, DA 3.0, DA 10.0 | 79781-1 | 79782-9 | uV |
| `b_implicit_ms` | DA 0.01, DA 3.0, DA 10.0 | 79786-0 | 79785-2 | ms |
| `a_amp_uv` | LA 3.0 | 79775-3 | 79776-1 | uV |
| `a_implicit_ms` | LA 3.0 | 79779-5 | 79780-3 | ms |
| `b_amp_uv` | LA 3.0 | 79783-7 | 79784-5 | uV |
| `b_implicit_ms` | LA 3.0 | 79787-8 | 79788-6 | ms |
| `b_amp_uv` | LA 30 Hz | 79795-1 | 79796-9 | uV |
| `b_implicit_ms` | LA 30 Hz | 79797-7 | 79798-5 | ms |
| `phnr_amp_uv` | LA 3.0 | project code | project code | uV |
| `ba_ratio` | DA 3.0, DA 10.0, LA 3.0 | project code | project code | 1 |

Source: Regenstrief Institute, LOINC panel 79894-2. LOINC does not separate DA 0.01, DA 3.0, and DA 10.0, so the `iscev-protocol` extension names the protocol. Project codes use the code system `https://ai-fairness.com/fhir/erg/CodeSystem/erg-features`, with the feature name as the code. The LOINC codes are eye-specific, so when the eye is not known, every value is sent under the project code system instead. Units use UCUM. The Traffic Light zones and the other features stay in the Layer 2 and Layer 4 report.

## Bundle

| Resource | Content |
|---|---|
| Observation | As above |
| DiagnosticReport | LOINC 79894-2; `conclusionCode` from the code system `…/CodeSystem/traffic-light` (`GREEN`, `AMBER`, or `RED`); `conclusion` from the Layer 2 summary; `result` points to the Observation |
| AuditEvent | Type DICOM `110100` (Application Activity); `outcome` `"0"` (success); the Layer 4 audit record as a JSON string in the `layer4-audit` extension |
| Patient | Included only when age or sex is supplied: age in whole years in the `age-years` extension, never the date of birth (GDPR Article 5(1)(c)) |

## Project extensions and code systems (Appendix B, Table B.2)

| Name | Kind | Used in |
|---|---|---|
| `iscev-protocol` | Extension (valueCode) | Observation |
| `electrode-type` | Extension (valueCode) | Observation |
| `version-stamp` | Extension with four parts (valueString) | Observation |
| `age-years` | Extension (valueInteger) | Patient |
| `layer4-audit` | Extension (valueString) | AuditEvent |
| `traffic-light` | Code system | DiagnosticReport |
| `erg-features` | Code system | Observation component |

Extensions live under `https://ai-fairness.com/fhir/erg/StructureDefinition/` and code systems under `https://ai-fairness.com/fhir/erg/CodeSystem/`.

## Example

The Bundle below was produced by the API for the sample file `data/samples/normal_001_DA3.csv` (DA 3.0, DTL fiber electrode), with the left eye, a recording center, a device, and the patient's age and sex supplied for illustration. The sample was made to demonstrate the code, so its values are not reference values. The Layer 4 record and the configuration hash are shortened.

```json
{
  "resourceType": "Bundle",
  "id": "00fd0150-b0db-4830-8159-00ff3eabaceb",
  "type": "collection",
  "timestamp": "2026-11-21T20:21:54+00:00",
  "entry": [
    {
      "fullUrl": "urn:uuid:9ba73070-6e34-45bb-b592-008a93050a5f",
      "resource": {
        "resourceType": "Observation",
        "id": "9ba73070-6e34-45bb-b592-008a93050a5f",
        "extension": [
          {
            "url": "https://ai-fairness.com/fhir/erg/StructureDefinition/iscev-protocol",
            "valueCode": "DA 3.0"
          },
          {
            "url": "https://ai-fairness.com/fhir/erg/StructureDefinition/electrode-type",
            "valueCode": "dtl_fiber"
          },
          {
            "url": "https://ai-fairness.com/fhir/erg/StructureDefinition/version-stamp",
            "extension": [
              {
                "url": "api_version",
                "valueString": "2.5.0"
              },
              {
                "url": "model_weights_hash",
                "valueString": "PENDING"
              },
              {
                "url": "config_hash",
                "valueString": "sha256:ac27c89617b2…"
              },
              {
                "url": "normative_ref_version",
                "valueString": "baker2025"
              }
            ]
          }
        ],
        "status": "final",
        "category": [
          {
            "coding": [
              {
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "procedure",
                "display": "Procedure"
              }
            ]
          }
        ],
        "code": {
          "coding": [
            {
              "system": "http://loinc.org",
              "code": "79894-2",
              "display": "Electroretinography (ERG) panel"
            }
          ]
        },
        "subject": {
          "reference": "Patient/P001"
        },
        "effectiveDateTime": "2026-06-22",
        "performer": [
          {
            "reference": "Organization/C01"
          }
        ],
        "bodySite": {
          "text": "Left eye (OS)"
        },
        "device": {
          "reference": "Device/DEVICE-01"
        },
        "component": [
          {
            "code": {
              "coding": [
                {
                  "system": "http://loinc.org",
                  "code": "79774-6"
                }
              ],
              "text": "a_amp_uv"
            },
            "valueQuantity": {
              "value": 131.6,
              "system": "http://unitsofmeasure.org",
              "code": "uV",
              "unit": "uV"
            }
          },
          {
            "code": {
              "coding": [
                {
                  "system": "http://loinc.org",
                  "code": "79778-7"
                }
              ],
              "text": "a_implicit_ms"
            },
            "valueQuantity": {
              "value": 17.5,
              "system": "http://unitsofmeasure.org",
              "code": "ms",
              "unit": "ms"
            }
          },
          {
            "code": {
              "coding": [
                {
                  "system": "http://loinc.org",
                  "code": "79782-9"
                }
              ],
              "text": "b_amp_uv"
            },
            "valueQuantity": {
              "value": 433.8,
              "system": "http://unitsofmeasure.org",
              "code": "uV",
              "unit": "uV"
            }
          },
          {
            "code": {
              "coding": [
                {
                  "system": "http://loinc.org",
                  "code": "79785-2"
                }
              ],
              "text": "b_implicit_ms"
            },
            "valueQuantity": {
              "value": 61.5,
              "system": "http://unitsofmeasure.org",
              "code": "ms",
              "unit": "ms"
            }
          },
          {
            "code": {
              "coding": [
                {
                  "system": "https://ai-fairness.com/fhir/erg/CodeSystem/erg-features",
                  "code": "ba_ratio"
                }
              ],
              "text": "ba_ratio"
            },
            "valueQuantity": {
              "value": 3.3,
              "system": "http://unitsofmeasure.org",
              "code": "1"
            }
          }
        ]
      }
    },
    {
      "fullUrl": "urn:uuid:f1638f2f-d26c-44f8-9a04-becec5a7b66e",
      "resource": {
        "resourceType": "Patient",
        "id": "P001",
        "extension": [
          {
            "url": "https://ai-fairness.com/fhir/erg/StructureDefinition/age-years",
            "valueInteger": 42
          }
        ],
        "gender": "female"
      }
    },
    {
      "fullUrl": "urn:uuid:72709321-92f2-44af-b240-2214134460c6",
      "resource": {
        "resourceType": "DiagnosticReport",
        "status": "final",
        "code": {
          "coding": [
            {
              "system": "http://loinc.org",
              "code": "79894-2",
              "display": "Electroretinography (ERG) panel"
            }
          ]
        },
        "subject": {
          "reference": "Patient/P001"
        },
        "result": [
          {
            "reference": "urn:uuid:9ba73070-6e34-45bb-b592-008a93050a5f"
          }
        ],
        "conclusion": "A Wave Implicit Time increased/delayed (Z=+3.9) B Wave Amplitude increased/delayed (Z=+10. …",
        "conclusionCode": [
          {
            "coding": [
              {
                "system": "https://ai-fairness.com/fhir/erg/CodeSystem/traffic-light",
                "code": "RED"
              }
            ]
          }
        ]
      }
    },
    {
      "fullUrl": "urn:uuid:20faec06-c22d-4788-8020-115b82c924ad",
      "resource": {
        "resourceType": "AuditEvent",
        "extension": [
          {
            "url": "https://ai-fairness.com/fhir/erg/StructureDefinition/layer4-audit",
            "valueString": "{\"report_id\": \"…\", \"pipeline_version\": \"2.5.0\", \"…\": \"…\"}"
          }
        ],
        "type": {
          "system": "http://dicom.nema.org/resources/ontology/DCM",
          "code": "110100",
          "display": "Application Activity"
        },
        "recorded": "2026-11-21T20:21:54+00:00",
        "outcome": "0",
        "agent": [
          {
            "who": {
              "display": "ERG Analysis API"
            },
            "requestor": false
          }
        ],
        "source": {
          "observer": {
            "reference": "Organization/C01"
          }
        }
      }
    }
  ]
}
```

## Checking the output

The test suite checks the panel code, the Table B.1 component codes, the project extensions, the version stamp, and the three resources of the Bundle (`tests/test_pipeline.py`, `TestFHIROutput`, and `tests/test_regression.py`, T-REG-06 and T-REG-07).
