import type { CurrentUser } from "@/types/api";

export function workspaceAccessAllowed(user: CurrentUser | null | undefined) {
  if (!user) {
    return true;
  }
  if (user.is_platform_admin && user.tenants.length === 0) {
    return true;
  }
  if (!user.subscription) {
    return true;
  }
  return user.subscription.access;
}

export function isSubscriptionLockedPath(pathname: string) {
  return pathname.startsWith("/app/billing") || pathname.startsWith("/app/settings");
}

export function postAuthPath(user: CurrentUser | null | undefined) {
  if (user?.is_platform_admin) {
    return "/platform";
  }
  if (user && !workspaceAccessAllowed(user)) {
    return "/app/billing";
  }
  return "/app/dashboard";
}
