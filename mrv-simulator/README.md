# VeriField Nexus — Test Environment (MRV Simulator)

This is a production-quality, browser-local Single Page Application (SPA) that simulates a real Measurement, Reporting, and Verification (MRV) system for environmental and energy installations.

It models the entire lifecycle of a clean climate asset: **Field Capture → Automated Verification Scoring → Solana On-Chain Anchoring (Mocked) → Monitoring & Analytics**.

## Key Features

1. **User Roles Control Switcher**:
   - **Field Agent**: Access to the capture form to register new assets.
   - **Verifier (Admin)**: Full administrative dashboard + access to the verification engine parameters and simulated blockchain ledger anchoring.
   - **Viewer**: Read-only access to dashboard statistics, maps, trends, and registry logs.

2. **Field Data Capture Module**:
   - Telemetry capture form for clean energy asset types (Cookstove, Solar, Hybrid Energy).
   - Auto-resolving GPS coordinates (using the browser's `navigator.geolocation` API with simulated fallback coordinate generation if permissions are denied).
   - Drag & Drop file upload zone simulating cryptographic photographic image signature hashing.
   - Presets for mock testing (including duplicate image credits fraud scenario).
   - Cryptographic payload hashing on submit.

3. **Verification Engine (Core Feature)**:
   - Evaluates submissions and generates a **Trust Score (0–100)**:
     - **Image Uniqueness (50%)**: Flags duplicate photographs recycled across different physical assets.
     - **GPS Integrity (30%)**: Detects suspicious coordinates jumps (>1km variance in <15min between sessions).
     - **Completeness (20%)**: Audits vital description metadata and evidence photo presence.
   - Assigns a **PASS / FAIL** threshold status (Trust Score >= 70 = PASS).
   - Dynamic replay simulator with scan timing animations and trust dial gauge arc.

4. **Solana Simulated Anchoring Layer**:
   - Mocks Solana blockchain ledger anchoring for verified climate assets.
   - Generates immutable block heights, slots, and 88-character cryptographic transaction signatures.

5. **Monitoring & Analytics Dashboard**:
   - Live Leaflet map displaying registry coordinate points styled dynamically by status (Verified, Flagged, Pending).
   - Interactive Chart.js stacked bar graph detailing submission counts, verification success, and anomaly rates over a 7-day rolling window.
   - Searchable, filterable MRV registry table.
   - Sliding detailed drawer detailing audit logs, transaction states, and CO₂ reduction estimates.
   - Export CSV function to download full local database registries.

## Getting Started

1. Navigate to the `mrv-simulator` directory:
   ```bash
   cd mrv-simulator
   ```

2. Open `index.html` in any web browser of your choice.

   *Alternatively, you can run a local HTTP development server from the repository root:*
   ```bash
   # Using Python (standard)
   python3 -m http.server 8080
   
   # Or using Node.js http-server
   npx http-server ./mrv-simulator -p 8080
   ```
   Then navigate to `http://localhost:8080` in your browser.

## Testing Guidelines

1. **Test Auto Geolocation**: Navigate to the **Field Capture** tab. Click **Auto Detect GPS**. Approve browser permissions to lock your actual coordinates, or decline to see the automatic East-African mock coordinate fallback.
2. **Test Duplicate Image Detection**: 
   - Under the photographic upload zone, click the quick preset **Cookstove A**. Fill in coordinates, add notes, and submit.
   - Next, create another entry but click the **Cookstove A (Dup)** preset. Submit the form.
   - In the **Dashboard** table, find the new record. You will notice it gets flagged automatically due to a low trust score.
   - Click the row, then click **Replay Verification** to see the engine detect the duplicate image hash signature.
3. **Test Solana Anchoring**:
   - Switch your active role in the header to **Verifier (Admin)**.
   - Select any pending record in the dashboard table.
   - Click **Anchor On Solana** in either the slide drawer or the Verification Inspector.
   - Notice the status updates to **Verified** and simulated transaction details are generated.
   - Inspect the **On-Chain Ledger** tab to see the immutable blockchain logs.
4. **Test CSV Export**: Click **Export CSV** on the dashboard to download the database registry as a standard spreadsheet file.
