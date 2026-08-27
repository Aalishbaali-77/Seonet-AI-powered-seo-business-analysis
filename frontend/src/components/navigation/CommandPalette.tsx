"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import SearchIcon from "@mui/icons-material/Search";
import { Dialog, DialogContent, List, ListItemButton, ListItemIcon, ListItemText, TextField } from "@mui/material";

import type { NavItem } from "@/config/navigation";
import { navIcon } from "@/config/navIcons";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { commandToggled } from "@/store/slices/uiSlice";

export function CommandPalette({ items }: { items: NavItem[] }) {
  const open = useAppSelector((state) => state.ui.commandOpen);
  const flags = useAppSelector((state) => state.ui.featureFlags);
  const product = useAppSelector((state) => state.ui.branding.product_name);
  const modules = useAppSelector((state) => state.auth.user?.modules ?? []);
  const access = useAppSelector((state) => state.auth.user?.subscription?.access !== false);
  const dispatch = useAppDispatch();
  const router = useRouter();
  const [query, setQuery] = useState("");

  const visible = useMemo(
    () =>
      items
        .flatMap((item) => [item, ...(item.children ?? [])])
        .filter((item) => !item.flag || flags[item.flag])
        .filter((item) => !item.module || modules.includes(item.module))
        .filter((item) => access || item.bypassLock)
        .filter((item) => item.label.toLowerCase().includes(query.toLowerCase())),
    [access, flags, items, modules, query],
  );

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        dispatch(commandToggled());
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [dispatch]);

  return (
    <Dialog
      open={open}
      onClose={() => dispatch(commandToggled(false))}
      fullWidth
      maxWidth="sm"
      fullScreen={false}
      sx={{ "& .MuiDialog-paper": { m: { xs: 1, sm: 2 } } }}
    >
      <DialogContent sx={{ p: 0 }}>
        <TextField
          autoFocus
          placeholder={`Search ${product}`}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          slotProps={{ input: { startAdornment: <SearchIcon sx={{ mr: 1 }} /> } }}
          sx={{ p: 2 }}
        />
        <List>
          {visible.map((item) => {
            const Icon = navIcon(item.id);
            return (
            <ListItemButton
              key={item.id}
              onClick={() => {
                router.push(item.href);
                dispatch(commandToggled(false));
              }}
            >
              <ListItemIcon sx={{ minWidth: 40, color: "text.secondary" }}>
                <Icon fontSize="small" />
              </ListItemIcon>
              <ListItemText primary={item.label} secondary={item.href} />
            </ListItemButton>
            );
          })}
        </List>
      </DialogContent>
    </Dialog>
  );
}
