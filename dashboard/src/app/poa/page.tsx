// =============================================================================
// VeriField Nexus — POA Route Redirector
// =============================================================================
// Performs server-side redirection of /poa to /dashboard/poa.
// =============================================================================

import { redirect } from "next/navigation";

export default function POARedirectPage() {
  redirect("/dashboard/poa");
}
