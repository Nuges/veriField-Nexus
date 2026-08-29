import { redirect } from "next/navigation";

export default function AccessControlPage() {
  redirect("/dashboard/people?tab=access");
}

