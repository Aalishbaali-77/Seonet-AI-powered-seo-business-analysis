"use client";

import { useState } from "react";
import { Alert, Button, Card, CardContent, Stack, TextField, Typography } from "@mui/material";

import { authApi } from "@/services/authApi";
import { authSucceeded } from "@/store/slices/authSlice";
import { useAppDispatch, useAppSelector } from "@/store/hooks";

export function ProfileSettings() {
  const dispatch = useAppDispatch();
  const user = useAppSelector((state) => state.auth.user);
  const [firstName, setFirstName] = useState(user?.first_name ?? "");
  const [lastName, setLastName] = useState(user?.last_name ?? "");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const [resetSent, setResetSent] = useState(false);

  if (!user) {
    return null;
  }

  const save = async () => {
    setSaving(true);
    setError("");
    setSaved(false);
    try {
      const updated = await authApi.updateProfile({ first_name: firstName, last_name: lastName });
      dispatch(authSucceeded(updated));
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update your profile.");
    } finally {
      setSaving(false);
    }
  };

  const sendPasswordReset = async () => {
    setError("");
    setResetSent(false);
    try {
      await authApi.requestPasswordReset(user.email);
      setResetSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to send the reset link.");
    }
  };

  return (
    <Stack spacing={3}>
      <Card variant="outlined">
        <CardContent>
          <Stack spacing={2}>
            <Typography variant="h4">Your profile</Typography>
            {error ? <Alert severity="error">{error}</Alert> : null}
            {saved ? <Alert severity="success">Profile updated.</Alert> : null}
            <TextField label="Email" value={user.email} disabled fullWidth helperText="Contact another platform admin to change your email." />
            <TextField label="First name" value={firstName} onChange={(event) => setFirstName(event.target.value)} fullWidth />
            <TextField label="Last name" value={lastName} onChange={(event) => setLastName(event.target.value)} fullWidth />
            <Stack direction="row">
              <Button variant="contained" onClick={() => void save()} disabled={saving}>
                Save changes
              </Button>
            </Stack>
          </Stack>
        </CardContent>
      </Card>
      <Card variant="outlined">
        <CardContent>
          <Stack spacing={2}>
            <Typography variant="h4">Password</Typography>
            <Typography color="text.secondary">
              For security, passwords are never shown or edited directly. We&apos;ll email you a secure link to set a new one.
            </Typography>
            {resetSent ? <Alert severity="success">Check {user.email} for a link to set a new password.</Alert> : null}
            <Stack direction="row">
              <Button variant="outlined" onClick={() => void sendPasswordReset()}>
                Send password reset link
              </Button>
            </Stack>
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
}
