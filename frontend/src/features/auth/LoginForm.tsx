"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Alert, Box, Button, Link as MuiLink, Stack, TextField, Typography } from "@mui/material";
import NextLink from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useForm } from "react-hook-form";

import { loginSchema, type LoginValues } from "@/features/auth/schemas";
import { postAuthPath } from "@/lib/authPaths";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { loginRequested } from "@/store/slices/authSlice";

export function LoginForm() {
  const dispatch = useAppDispatch();
  const { status, submitting, error, user } = useAppSelector((state) => state.auth);
  const branding = useAppSelector((state) => state.ui.branding);
  const router = useRouter();
  const isDev = process.env.NODE_ENV === "development";
    const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  useEffect(() => {
    if (status === "authenticated" && user) {
      router.replace(postAuthPath(user));
    }
  }, [router, status, user]);

  return (
    <Box component="form" onSubmit={form.handleSubmit((values) => dispatch(loginRequested(values)))} noValidate>
      <Stack spacing={2}>
        <Typography variant="h2">Sign in</Typography>
        <Typography color="text.secondary">Access your {branding.product_name} workspace.</Typography>
        {error ? <Alert severity="error">{error}</Alert> : null}

                {isDev ? (
          <Alert severity="info">
            Platform owner: owner@sigbl.com / owner@123
            <br />
            Tenant admin: demo@sigbl.com / demo@123
          </Alert>
        ) : null}

        <TextField label="Email" type="email" autoComplete="email" {...form.register("email")} error={Boolean(form.formState.errors.email)} helperText={form.formState.errors.email?.message} />
        <TextField label="Password" type="password" autoComplete="current-password" {...form.register("password")} error={Boolean(form.formState.errors.password)} helperText={form.formState.errors.password?.message} />
        <Button type="submit" variant="contained" size="large" disabled={submitting}>
          {submitting ? "Signing in…" : "Sign in"}
        </Button>
        <Stack direction="row" sx={{ justifyContent: "space-between" }}>
          <MuiLink component={NextLink} href="/forgot-password" variant="body2">
            Forgot password
          </MuiLink>
          <MuiLink component={NextLink} href="/register" variant="body2">
            Create workspace
          </MuiLink>
        </Stack>
        {branding.login_footer ? (
          <Typography variant="caption" color="text.secondary">
            {branding.login_footer}
          </Typography>
        ) : null}
      </Stack>
    </Box>
  );
}
