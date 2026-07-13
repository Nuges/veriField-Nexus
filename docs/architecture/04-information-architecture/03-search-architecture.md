# Enterprise Search Architecture

Enterprise search provides fast, faceted, and spatial querying across millions of records without degrading operational database performance.

## 1. Search Engine Typology

1. **Global Unified Search:** The omnibar at the top of the CIOS UI. Searches across Projects, Assets, Users, and Organizations.
2. **Domain/Faceted Search:** Table-level filtering within modules (e.g., filtering Projects by Sector, Status, and VVB).
3. **Spatial Search:** Geographic querying (e.g., "Find all assets within 5km of this forest boundary").
4. **Evidence / Full-Text Search:** Searching the contents of PDDs, Audit Reports, and OCR'd contracts.

## 2. Infrastructure

- **Operational Database (PostgreSQL):** Handles exact-match queries and simple filtering using B-Tree and GIN indexes.
- **Search Cluster (Elasticsearch / OpenSearch):** A dedicated search index that asynchronously consumes database CDC (Change Data Capture) streams. Used for Full-Text Search and fuzzy matching.
- **Spatial Engine (PostGIS):** Handles all geospatial queries (intersections, containment).

## 3. Data Synchronization

To keep the Search Cluster up to date without synchronous overhead:
1. The Operational Database emits WAL (Write-Ahead Log) changes.
2. A CDC tool (e.g., Debezium) streams these changes to an Event Bus (Kafka).
3. An Indexing Worker consumes the events, denormalizes the data (e.g., attaching Organization Name to an Asset record), and updates the Search Cluster.

## 4. Search Authorization

Search results must strictly adhere to the user's ABAC/RBAC context. 
- A Field Agent searching for "Project Alpha" will only see it if they are explicitly assigned to it.
- A Regulator searching for "Project Alpha" will see it if it falls within their Jurisdiction.
- The Indexing Worker embeds `tenant_id` and an `acl_list` (Access Control List array) directly into the search document, allowing the Search Cluster to filter out inaccessible records before returning results to the API Gateway.
