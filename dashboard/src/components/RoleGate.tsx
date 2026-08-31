"use client";

import React, { ReactNode } from "react";
import { useWorkspace } from "@/context/WorkspaceContext";
import { ActionPermission, canPerformAction, CanonicalRole, normalizeRole } from "@/lib/roles";

interface RoleGateProps {
  action?: ActionPermission;
  allowedRoles?: CanonicalRole[];
  children: ReactNode;
  fallback?: ReactNode;
  hideIfUnauthorized?: boolean;
}

/**
 * Reusable UI component that conditionally renders or disables mutation controls
 * based on the user's canonical role and authorized action permissions.
 */
export function RoleGate({
  action,
  allowedRoles,
  children,
  fallback = null,
  hideIfUnauthorized = true,
}: RoleGateProps) {
  const { user } = useWorkspace();
  const canonicalRole = normalizeRole(user?.role);

  let isAuthorized = false;

  if (action) {
    isAuthorized = canPerformAction(action, user?.role);
  } else if (allowedRoles && allowedRoles.length > 0) {
    isAuthorized =
      canonicalRole === "SUPER_ADMIN" || allowedRoles.includes(canonicalRole);
  } else {
    isAuthorized = true;
  }

  if (isAuthorized) {
    return <>{children}</>;
  }

  if (hideIfUnauthorized) {
    return <>{fallback}</>;
  }

  return <div className="opacity-40 pointer-events-none cursor-not-allowed select-none">{children}</div>;
}
