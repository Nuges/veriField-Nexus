# Checklist: Modular Climate Operating System & Isolation Refactor

## Phase 1: Module Registry & Frontend Core Decoupling
- `[x]` 1. Create [moduleRegistry.ts](file:///Users/segun/Documents/Verifield%20nexus/dashboard/src/lib/moduleRegistry.ts) defining `MODULE_REGISTRY` mapping modules (`cookstove`, `energy`, `carbon`) and their owned KPIs, charts, and attributes.
- `[x]` 2. Delete/replace [sectorConfig.ts](file:///Users/segun/Documents/Verifield%20nexus/dashboard/src/lib/sectorConfig.ts).
- `[x]` 3. Refactor [WorkspaceContext.tsx](file:///Users/segun/Documents/Verifield%20nexus/dashboard/src/context/WorkspaceContext.tsx) to resolve from the registry, enforce strict sector validation checks, and lock `field_agent` profiles to their defined module scope.
- `[x]` 4. Update [layout.tsx](file:///Users/segun/Documents/Verifield%20nexus/dashboard/src/app/dashboard/layout.tsx) and [Sidebar.tsx](file:///Users/segun/Documents/Verifield%20nexus/dashboard/src/components/Sidebar.tsx) to hide selector switchers for `field_agent` role.

## Phase 2: Isolated Dashboard & Component Rendering
- `[x]` 5. Refactor Dashboard [page.tsx](file:///Users/segun/Documents/Verifield%20nexus/dashboard/src/app/dashboard/page.tsx) to render strictly module-scoped KPIs, charts, and maps. Remove any `allKpis` patterns or opacity filters.
- `[x]` 6. Implement and verify strict isolation in operational views:
  - `[x]` Properties [page.tsx](file:///Users/segun/Documents/Verifield%20nexus/dashboard/src/app/dashboard/properties/page.tsx)
  - `[x]` Activities [page.tsx](file:///Users/segun/Documents/Verifield%20nexus/dashboard/src/app/dashboard/activities/page.tsx)
  - `[x]` Audits [page.tsx](file:///Users/segun/Documents/Verifield%20nexus/dashboard/src/app/dashboard/audits/page.tsx)
  - `[x]` Map [page.tsx](file:///Users/segun/Documents/Verifield%20nexus/dashboard/src/app/dashboard/map/page.tsx)
  - `[x]` Carbon [page.tsx](file:///Users/segun/Documents/Verifield%20nexus/dashboard/src/app/dashboard/carbon/page.tsx)
  - `[x]` Sensors [page.tsx](file:///Users/segun/Documents/Verifield%20nexus/dashboard/src/app/dashboard/sensors/page.tsx)
- `[x]` 7. Refactor Executive Portfolio [page.tsx](file:///Users/segun/Documents/Verifield%20nexus/dashboard/src/app/dashboard/executive/page.tsx) to serve as the exclusive cross-module analytics page.

## Phase 3: Backend Server-Side Enforcement & Scoping
- `[x]` 8. Update [security.py](file:///Users/segun/Documents/Verifield%20nexus/backend/app/core/security.py) user profile loading and dependency scopes to resolve user-specific permissions.
- `[x]` 9. Refactor backend endpoints to enforce module scoping on database queries (using `User.sector` to override parameter inputs for `field_agent` roles):
  - `[x]` Activities API in [activities.py](file:///Users/segun/Documents/Verifield%20nexus/backend/app/api/v1/activities.py)
  - `[x]` Properties API in [properties.py](file:///Users/segun/Documents/Verifield%20nexus/backend/app/api/v1/properties.py)
  - `[x]` Carbon Ledger API in [carbon.py](file:///Users/segun/Documents/Verifield%20nexus/backend/app/api/v1/carbon.py)
  - `[x]` Audits API in [audits.py](file:///Users/segun/Documents/Verifield%20nexus/backend/app/api/v1/audits.py)
  - `[x]` Analytics API in [analytics.py](file:///Users/segun/Documents/Verifield%20nexus/backend/app/api/v1/analytics.py)
  - `[x]` Export API in [export.py](file:///Users/segun/Documents/Verifield%20nexus/backend/app/api/v1/export.py)

## Phase 4: Automated Testing & Verification
- `[x]` 10. Create new unit/integration tests in [test_module_isolation.py](file:///Users/segun/Documents/Verifield%20nexus/backend/tests/test_module_isolation.py) validating:
  - `[x]` KPI isolation
  - `[x]` Activity and Property database query isolation
  - `[x]` Field agent permission scoping (parameter manipulation protection)
  - `[x]` Executive Portfolio cross-sector aggregation access
- `[x]` 11. Run pytest suite and frontend compile validation:
  - `[x]` `venv/bin/pytest`
  - `[x]` `npm run build`

## Phase 5: Documentation & Blueprint Handover
- `[x]` 12. Create / Update the final deliverables walkthrough detailing system architecture, permissions, backend flow, and expansion blueprint.
