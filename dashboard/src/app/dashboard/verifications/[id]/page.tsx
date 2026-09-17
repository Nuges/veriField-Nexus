"use client";

import { useParams } from "next/navigation";
import AuditorWorkspaceView from "@/components/verification/AuditorWorkspaceView";

export default function VerificationPackageDetailPage() {
  const params = useParams();
  const packageId = params.id as string;

  return <AuditorWorkspaceView packageId={packageId} />;
}
