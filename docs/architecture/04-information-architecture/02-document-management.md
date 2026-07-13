# Document & Evidence Management Architecture

VeriField Nexus processes massive volumes of unstructured data (documents, photos, satellite imagery, contracts). This architecture ensures secure storage, cryptographic verification, and lifecycle retention.

## 1. Storage Tiers & Mechanisms

1. **Hot Storage (S3 Standard / Cloud Storage):**
   - **Use Case:** Active evidence collection, pending verification photos, actively viewed contracts.
   - **Access:** High-speed, signed URLs.
2. **Cold Storage (S3 Glacier / Deep Archive):**
   - **Use Case:** Historical audits, retired credits, compliance retention.
   - **Access:** Async retrieval (12-48 hours). Records transition to cold storage automatically 1 year after the associated carbon credit is retired.

## 2. Evidence Immutability Workflow

To prevent fraud (e.g., tampering with GPS coordinates in a field photo), the platform enforces an immutability chain:
1. **Edge Hashing:** The mobile app generates a SHA-256 hash of the photo immediately upon capture.
2. **Secure Upload:** The photo is uploaded to object storage via a short-lived Signed URL.
3. **Database Ledger:** The `Evidence` table records the S3 URI alongside the generated SHA-256 hash.
4. **Verification:** Any subsequent retrieval of the file automatically re-hashes the object and compares it to the database record. A mismatch triggers an immediate `EvidenceTampered` security event.

## 3. Supported Evidence Types

| Type | Examples | Metadata Extracted |
| :--- | :--- | :--- |
| **Media** | Photos, Videos, Audio | EXIF Data, GPS, Timestamp, Device ID |
| **Documents** | PDDs, Contracts, Audit Reports | OCR Text, Signatures, Page Count |
| **Telemetry** | IoT Payloads, Smart Meter Logs | Sensor ID, Timeseries Metrics |
| **Spatial** | GeoJSON, KML, Satellite TIFFs | Polygons, Bounding Boxes |

## 4. Archiving and Retention Policies

Retention policies are driven by Governance rules (e.g., National Registries often require 10-year retention).
- **Deletion:** Users cannot delete evidence once it is linked to a registered project. They can only mark it `INVALID` (e.g., a blurry photo). The original file is retained for the audit log.
- **Data Subject Rights (GDPR/CCPA):** If a document contains PII (e.g., a homeowner's contract), it is tagged with a `contains_pii` flag. Upon a valid deletion request, the file is scrubbed, but a cryptographic tombstone remains in the database to satisfy carbon auditing requirements.
