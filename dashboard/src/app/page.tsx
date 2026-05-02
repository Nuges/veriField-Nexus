// =============================================================================
// VeriField Nexus — Root Page (Redirect)
// =============================================================================

import { redirect } from "next/navigation";

export default function RootPage() {
  redirect("/login");
}
