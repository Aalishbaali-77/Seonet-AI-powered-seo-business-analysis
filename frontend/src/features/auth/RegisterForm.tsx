"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Alert, Box, Button, Link as MuiLink, Stack, TextField, Typography } from "@mui/material";
import NextLink from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useForm } from "react-hook-form";

import { registerSchema, type RegisterValues } from "@/features/auth/schemas";
import { postAuthPath } from "@/lib/authPaths";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { registerRequested } from "@/store/slices/authSlice";

export function RegisterForm() {
  const dispatch = useAppDispatch();
  const { status, submitting, error, user } = useAppSelector((state) => state.auth);
  const branding = useAppSelector((state) => state.ui.branding);
  const router = useRouter();
  const form = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { name: "", email: "", password: "" },
  });

  useEffect(() => {
    if (status === "authenticated" && user) {
      router.replace(postAuthPath(user));
    }
  }, [router, status, user]);

  return (
    <Box component="form" onSubmit={form.handleSubmit((values) => dispatch(registerRequested(values)))} noValidate>
      <Stack spacing={2}>
        <Typography variant="h2">Create your workspace</Typography>
        <Typography color="text.secondary">
          Enter your work email. {branding.product_name} creates your tenant and makes you the owner — you can invite people after you sign in.
        </Typography>
        {error ? <Alert severity="error">{error}</Alert> : null}
        <TextField label="Your name" autoComplete="name" {...form.register("name")} helperText="Optional." />
        <TextField
          label="Work email"
          type="email"
          autoComplete="email"
          {...form.register("email")}
          error={Boolean(form.formState.errors.email)}
          helperText={form.formState.errors.email?.message}
        />
        <TextField
          label="Password"
          type="password"
          autoComplete="new-password"
          {...form.register("password")}
          error={Boolean(form.formState.errors.password)}
          helperText={form.formState.errors.password?.message ?? "At least 8 characters."}
        />
        <Button type="submit" variant="contained" size="large" disabled={submitting}>
          {submitting ? "Creating workspace…" : "Get started"}
        </Button>
        <MuiLink component={NextLink} href="/login" variant="body2">
          Already have an account? Sign in
        </MuiLink>
      </Stack>
    </Box>
  );
}
