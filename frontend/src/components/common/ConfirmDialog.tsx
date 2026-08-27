"use client";

import { Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle } from "@mui/material";
import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react";

export type ConfirmOptions = {
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
};

type ConfirmFn = (options: ConfirmOptions) => Promise<boolean>;

const ConfirmContext = createContext<ConfirmFn | null>(null);

export function useConfirm(): ConfirmFn {
  const confirm = useContext(ConfirmContext);
  if (!confirm) {
    throw new Error("useConfirm must be used within ConfirmProvider");
  }
  return confirm;
}

export function ConfirmProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const [options, setOptions] = useState<ConfirmOptions>({ title: "" });
  const resolveRef = useRef<((value: boolean) => void) | null>(null);

  const confirm = useCallback<ConfirmFn>((next) => {
    if (resolveRef.current) {
      resolveRef.current(false);
    }
    return new Promise<boolean>((resolve) => {
      resolveRef.current = resolve;
      setOptions(next);
      setOpen(true);
    });
  }, []);

  const finish = useCallback((value: boolean) => {
    setOpen(false);
    resolveRef.current?.(value);
    resolveRef.current = null;
  }, []);

  const descriptionId = options.description ? "sipulse-confirm-description" : undefined;

  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      <Dialog
        open={open}
        onClose={() => finish(false)}
        fullWidth
        maxWidth="xs"
        aria-labelledby="sipulse-confirm-title"
        aria-describedby={descriptionId}
      >
        <DialogTitle id="sipulse-confirm-title">{options.title}</DialogTitle>
        {options.description ? (
          <DialogContent>
            <DialogContentText id={descriptionId}>{options.description}</DialogContentText>
          </DialogContent>
        ) : null}
        <DialogActions>
          <Button onClick={() => finish(false)} autoFocus={options.danger !== false}>
            {options.cancelLabel ?? "Cancel"}
          </Button>
          <Button
            variant="contained"
            color={options.danger === false ? "primary" : "error"}
            onClick={() => finish(true)}
            autoFocus={options.danger === false}
          >
            {options.confirmLabel ?? "Confirm"}
          </Button>
        </DialogActions>
      </Dialog>
    </ConfirmContext.Provider>
  );
}
