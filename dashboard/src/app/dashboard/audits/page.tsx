import { redirect } from "next/navigation";

export default function AuditsRedirectPage() {
  redirect("/dashboard/verifications?tab=audits");
}
