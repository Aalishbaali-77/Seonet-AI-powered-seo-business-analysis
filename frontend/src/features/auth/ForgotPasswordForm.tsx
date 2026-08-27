"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Alert, Box, Button, Link as MuiLink, Stack, TextField, Typography } from "@mui/material";
import NextLink from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { forgotPasswordSchema, type ForgotPasswordValues } from "@/features/auth/schemas";
import { authApi } from "@/services/authApi";

export function ForgotPasswordForm() {
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const form = useForm<ForgotPasswordValues>({ resolver: zodResolver(forgotPasswordSchema), defaultValues: { email: "" } });

  return (
    <Box
      component="form"
      onSubmit={form.handleSubmit(async (values) => {
        setError(null);
        try {
          await authApi.requestPasswordReset(values.email);
          setSent(true);
        } catch (err) {
          setError(err instanceof Error ? err.message : "Unable to send reset email.");
        }
      })}
      noValidate
    >
      <Stack spacing={2}>
        <Typography variant="h2">Reset password</Typography>
        <Typography color="text.secondary">We will email a reset link if the account exists.</Typography>
        {error ? <Alert severity="error">{error}</Alert> : null}
        {sent ? <Alert severity="success">If that email is registered, a reset link is on its way.</Alert> : null}
        <TextField label="Email" type="email" {...form.register("email")} error={Boolean(form.formState.errors.email)} helperText={form.formState.errors.email?.message} />
        <Button type="submit" variant="contained" size="large">
          Send reset link
        </Button>
        <MuiLink component={NextLink} href="/login" variant="body2">
          Back to sign in
        </MuiLink>
      </Stack>
    </Box>
  );
}
