"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { CircularProgress, Stack } from "@mui/material";

import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { bootstrapRequested } from "@/store/slices/authSlice";
import { isSubscriptionLockedPath, workspaceAccessAllowed } from "@/lib/authPaths";

export function AuthGate({ children, platformOnly = false }: { children: React.ReactNode; platformOnly?: boolean }) {
  const { status, user } = useAppSelector((state) => state.auth);
  const dispatch = useAppDispatch();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (status === "idle") {
      dispatch(bootstrapRequested());
    }
  }, [dispatch, status]);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [pathname, router, status]);

  useEffect(() => {
    if (status !== "authenticated" || !user) {
      return;
    }
    if (platformOnly && !user.is_platform_admin) {
      router.replace("/app/dashboard");
      return;
    }
    if (!platformOnly && user.is_platform_admin && user.tenants.length === 0 && pathname.startsWith("/app")) {
      router.replace("/platform");
      return;
    }
    if (!platformOnly && pathname.startsWith("/app") && !workspaceAccessAllowed(user) && !isSubscriptionLockedPath(pathname)) {
      router.replace("/app/billing");
    }
  }, [pathname, platformOnly, router, status, user]);

  if (status !== "authenticated") {
    return (
      <Stack sx={{ alignItems: "center", justifyContent: "center", minHeight: "100vh" }}>
        <CircularProgress aria-label="Loading session" />
      </Stack>
    );
  }

  if (platformOnly && user && !user.is_platform_admin) {
    return null;
  }

  if (!platformOnly && user?.is_platform_admin && user.tenants.length === 0) {
    return (
      <Stack sx={{ alignItems: "center", justifyContent: "center", minHeight: "100vh" }}>
        <CircularProgress aria-label="Opening platform console" />
      </Stack>
    );
  }

  if (!platformOnly && user && pathname.startsWith("/app") && !workspaceAccessAllowed(user) && !isSubscriptionLockedPath(pathname)) {
    return (
      <Stack sx={{ alignItems: "center", justifyContent: "center", minHeight: "100vh" }}>
        <CircularProgress aria-label="Opening subscription" />
      </Stack>
    );
  }

  return children;
}
