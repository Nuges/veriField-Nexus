# Enterprise UI Architecture

The User Interface of VeriField Nexus must support drastically different personas—from a Regulator visualizing national spatial maps on a 4K monitor to a Field Agent filling out evidence forms on a low-end mobile device in offline mode.

## 1. UI Principles

- **No Mockups:** UI Architecture defines layout regions, widget interactions, state management, and permission bindings. Visual design is delegated to the Design System.
- **Role-Based Workspaces:** The UI dynamically reconfigures based on the authenticated user's Role and Organization. A Field Agent and a Super Admin logging into the exact same URL will see entirely different dashboards.
- **Skeleton Loading & Optimistic UI:** Complex aggregate queries (e.g., rendering the Carbon Yield chart) must use skeleton loaders so the primary interface doesn't block. Simple mutations (like checking a verification box) use Optimistic UI updates.

## 2. Core Layout Architecture

The application utilizes a persistent "Application Shell" pattern.

### 2.1 The Omnibar (Header)
- **Purpose:** Global navigation, Tenant Switching, Global Search, and Notification Center.
- **Audience:** All Users.
- **API Dependencies:** `/api/v1/auth/me`, `/api/v1/notifications`, `/api/v1/search`.

### 2.2 The Workspace Navigation (Sidebar)
- **Purpose:** Contextual navigation bounded by the user's current Domain (e.g., "Operations" vs "Governance").
- **Dynamic Rendering:** Driven by the `Capabilities Matrix`. If the user lacks the `jurisdiction:read` permission, the entire "Governance" menu item is omitted from the DOM.

### 2.3 The Main View Area
- **Purpose:** Renders the specific Module interface (Tables, Forms, Maps, Dashboards).
- **Error States:** Handled via global Error Boundaries. 403 Forbidden responses trigger a friendly "Access Denied" view without crashing the SPA.

## 3. UI Component Architecture

Complex screens are broken down into isolated, data-fetching Widgets.

*Example: The Project Detail Screen*
- **Header Widget:** Fetches basic project metadata (Name, Status).
- **Spatial Map Widget:** Fetches GeoJSON from the spatial service. Renders asynchronously.
- **Asset Data Table Widget:** Fetches paginated list of deployed assets.
- **Audit History Timeline Widget:** Fetches immutable ledger events.

If the Spatial Map Widget fails (e.g., GIS API timeout), it renders an isolated error state, allowing the user to continue interacting with the Asset Data Table.

## 4. State Management
- **Server State:** Handled by data-fetching libraries (e.g., React Query or Apollo GraphQL). The UI does not cache business logic locally.
- **Client State:** Minimal. Used only for temporary UI states (modal open/closed, current tab index).

## 5. Offline & Progressive Web App (PWA) Architecture
Field execution apps must function offline.
- **Local Database (IndexedDB / SQLite):** Caches assigned tasks, blank forms, and previously downloaded assets.
- **Mutation Queue:** When a Field Agent uploads a photo offline, the action is serialized into a queue.
- **Sync Engine:** Upon reconnecting, the Sync Engine processes the queue sequentially, handling conflict resolution if an asset state changed remotely during the offline period.
