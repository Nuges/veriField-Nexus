# 09 — Database ERD & Entity Relationships



## PostgreSQL Entity-Relationship Diagram



```mermaid

erDiagram

    ORGANIZATIONS ||--o{ USERS : "employs"

    ORGANIZATIONS ||--o{ PROJECTS : "owns"

    ORGANIZATIONS ||--o{ SYSTEM_SETTINGS : "configures"



    METHODOLOGY_FAMILIES ||--o{ METHODOLOGIES : "contains"

    METHODOLOGY_FAMILIES ||--o{ PROJECTS : "categorizes"

    METHODOLOGIES ||--o{ PROJECTS : "governs"



    PROJECTS ||--o{ PROPERTIES : "includes"

    PROJECTS ||--o{ VERIFICATION_TASKS : "audits"



    PROPERTIES ||--o{ ACTIVITIES : "records"

    PROPERTIES ||--o{ VERIFICATION_TASKS : "monitors"



    USERS ||--o{ ACTIVITIES : "submits"

    USERS ||--o{ VERIFICATION_TASKS : "verifies"

    USERS ||--o{ SIGNATURES : "signs"



    ORGANIZATIONS {

        uuid id PK

        string name

        jsonb licensed_sectors

        jsonb licensed_methodologies

        string plan

    }



    USERS {

        uuid id PK

        uuid organization_id FK

        string full_name

        string email

        string role

        boolean is_active

    }



    PROJECTS {

        uuid id PK

        uuid organization_id FK

        uuid methodology_id FK

        string project_code

        string name

        string country

        float diesel_emission_factor

        float grid_emission_factor

    }



    PROPERTIES {

        uuid id PK

        uuid project_id FK

        string name

        string property_type

        float latitude

        float longitude

        jsonb sustainability_metrics

    }



    ACTIVITIES {

        uuid id PK

        uuid asset_id FK

        uuid user_id FK

        float latitude

        float longitude

        string stove_id

        string household_id

        string image_hash

        timestamp captured_at

    }



    VERIFICATION_TASKS {

        uuid id PK

        uuid asset_id FK

        uuid verifier_id FK

        string status

        timestamp deadline

    }

```



---



## Database Partitioning Scheme

- Table `activities` is partitioned monthly (`activities_y2026m07`, etc.) based on `captured_at` for high-throughput IoT scale.
