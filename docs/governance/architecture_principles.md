# Architecture Principles

The VeriField Nexus architecture is governed by immutable principles. These principles serve as the ultimate authority during technical design decisions and dispute resolutions.

## 1. Architecture is Law
The overarching architectural design (Domain-Driven, Event-Driven, Metadata-First) cannot be circumvented for short-term velocity. Temporary hacks that violate the architecture are strictly forbidden in production.

## 2. Metadata is the Single Source of Truth
The platform must remain universally agnostic to specific methodologies, sectors, or project types. All domain logic, schemas, workflows, and constraints must be defined via metadata payloads loaded into the database, not hardcoded into the application layer.

## 3. Configuration over Code
Whenever possible, application behavior should be toggled, adjusted, and defined by centralized configuration engines rather than deep code-level branches.

## 4. Zero Hardcoding
There are absolutely zero exceptions for hardcoding external integrations, methodologies (e.g., "cookstove", "biochar"), roles, or specific logic pathways. All specific logic must be generalized into configurable rules engines or externalized plugins.

## 5. Universal Components
The Frontend and Mobile applications must rely on dynamic, metadata-driven universal components (e.g., `DynamicSchemaRenderer`, `UniversalMethodologyViewer`). Custom, static UI screens for specific methodologies are prohibited.

## 6. Composable Domains
The system is divided into autonomous, bounded domains. Domains must not tightly couple to the internal implementations of other domains. Communication between domains must occur via well-defined API contracts or the asynchronous Event Bus.

## 7. Domain-Driven Design (DDD)
The codebase structure inherently reflects the business domain. Each domain handles its own models, schemas, repositories, and services independently. 

## 8. Event-Driven Architecture (EDA)
State changes that affect multiple domains must be broadcast asynchronously via the core Event Bus. Synchronous domain-to-domain coupling is discouraged to prevent cascading failures.

## 9. Digital Twin First
Physical real-world assets (sensors, kilns, biochar batches, artisans) must be modeled explicitly as Digital Twins. Data flows originate from or map to a Digital Twin before being processed for compliance or carbon accounting.

## 10. Protocol Agnostic Hardware Layer
The IIoT Edge layer and backend gateways must abstract underlying hardware communication (MQTT, OPC-UA, HTTP, Modbus) into normalized telemetry schemas. The core logic must never depend on a specific hardware protocol.

## 11. Registry Agnostic Integration Layer
The system must be capable of integrating with any global carbon registry (Verra, Gold Standard, Puro.earth) via a normalized integration layer. Registry-specific API nuances must be abstracted away from the core methodology engine.
