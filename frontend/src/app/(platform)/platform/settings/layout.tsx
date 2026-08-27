"use client";

import { Box, Tab, Tabs } from "@mui/material";
import { usePathname, useRouter } from "next/navigation";

import { PageHeader } from "@/components/common/PageHeader";

const TABS = [
  { value: "profile", label: "Profile", href: "/platform/settings/profile" },
  { value: "team", label: "Team & Access", href: "/platform/settings/team" },
  { value: "appearance", label: "Appearance", href: "/platform/settings/appearance" },
];

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const active = TABS.find((tab) => pathname?.startsWith(tab.href))?.value ?? "profile";

  return (
    <Box>
      <PageHeader
        eyebrow="Platform"
        title="Settings"
        description="Manage your profile, platform admins, and workspace appearance."
      />
      <Tabs
        value={active}
        onChange={(_event, value: string) => {
          const tab = TABS.find((item) => item.value === value);
          if (tab) router.push(tab.href);
        }}
        sx={{ mb: 3, borderBottom: 1, borderColor: "divider" }}
      >
        {TABS.map((tab) => (
          <Tab key={tab.value} value={tab.value} label={tab.label} />
        ))}
      </Tabs>
      {children}
    </Box>
  );
}
