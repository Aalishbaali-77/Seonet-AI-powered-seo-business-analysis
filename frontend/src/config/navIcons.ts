import AccountBalanceOutlined from "@mui/icons-material/AccountBalanceOutlined";
import AdminPanelSettingsOutlined from "@mui/icons-material/AdminPanelSettingsOutlined";
import AssessmentOutlined from "@mui/icons-material/AssessmentOutlined";
import AutoAwesomeOutlined from "@mui/icons-material/AutoAwesomeOutlined";
import AutoFixHighOutlined from "@mui/icons-material/AutoFixHighOutlined";
import BadgeOutlined from "@mui/icons-material/BadgeOutlined";
import BusinessOutlined from "@mui/icons-material/BusinessOutlined";
import CampaignOutlined from "@mui/icons-material/CampaignOutlined";
import CardMembershipOutlined from "@mui/icons-material/CardMembershipOutlined";
import ContactsOutlined from "@mui/icons-material/ContactsOutlined";
import CorporateFareOutlined from "@mui/icons-material/CorporateFareOutlined";
import EventNoteOutlined from "@mui/icons-material/EventNoteOutlined";
import ExtensionOutlined from "@mui/icons-material/ExtensionOutlined";
import FactCheckOutlined from "@mui/icons-material/FactCheckOutlined";
import HistoryOutlined from "@mui/icons-material/HistoryOutlined";
import HandshakeOutlined from "@mui/icons-material/HandshakeOutlined";
import InsightsOutlined from "@mui/icons-material/InsightsOutlined";
import KeyOutlined from "@mui/icons-material/KeyOutlined";
import Inventory2Outlined from "@mui/icons-material/Inventory2Outlined";
import LanguageOutlined from "@mui/icons-material/LanguageOutlined";
import ListAltOutlined from "@mui/icons-material/ListAltOutlined";
import PeopleOutlined from "@mui/icons-material/PeopleOutlined";
import PersonSearchOutlined from "@mui/icons-material/PersonSearchOutlined";
import ReceiptLongOutlined from "@mui/icons-material/ReceiptLongOutlined";
import RequestQuoteOutlined from "@mui/icons-material/RequestQuoteOutlined";
import SearchOutlined from "@mui/icons-material/SearchOutlined";
import SettingsOutlined from "@mui/icons-material/SettingsOutlined";
import SpaceDashboardOutlined from "@mui/icons-material/SpaceDashboardOutlined";
import StorefrontOutlined from "@mui/icons-material/StorefrontOutlined";
import PublicOutlined from "@mui/icons-material/PublicOutlined";
import LightbulbOutlined from "@mui/icons-material/LightbulbOutlined";
import TravelExploreOutlined from "@mui/icons-material/TravelExploreOutlined";
import ViewModuleOutlined from "@mui/icons-material/ViewModuleOutlined";
import type { SvgIconComponent } from "@mui/icons-material";

export const navIcons: Record<string, SvgIconComponent> = {
  dashboard: SpaceDashboardOutlined,
  ask: SearchOutlined,
  business: StorefrontOutlined,
  "business-overview": StorefrontOutlined,
  "business-sales": RequestQuoteOutlined,
  "business-products": Inventory2Outlined,
  "business-customers": PeopleOutlined,
  "business-ecommerce": StorefrontOutlined,
  "business-geography": PublicOutlined,
  "business-advisor": AutoAwesomeOutlined,
  markets: PublicOutlined,
  "market-overview": PublicOutlined,
  "market-demand": InsightsOutlined,
  "market-places": TravelExploreOutlined,
  "market-competition": HandshakeOutlined,
  "market-segments": PeopleOutlined,
  "market-scoring": AssessmentOutlined,
  "market-advisor": AutoAwesomeOutlined,
  opportunities: LightbulbOutlined,
  "opportunity-list": LightbulbOutlined,
  "opportunity-advisor": AutoAwesomeOutlined,
  intelligence: TravelExploreOutlined,
  websites: LanguageOutlined,
  audits: FactCheckOutlined,
  seo: SearchOutlined,
  aeo: AutoAwesomeOutlined,
  performance: InsightsOutlined,
  leads: PersonSearchOutlined,
  discover: TravelExploreOutlined,
  lists: ListAltOutlined,
  enrichment: AutoFixHighOutlined,
  scoring: InsightsOutlined,
  "lead-advisor": AutoAwesomeOutlined,
  crm: HandshakeOutlined,
  "crm-leads": PeopleOutlined,
  companies: BusinessOutlined,
  contacts: ContactsOutlined,
  deals: HandshakeOutlined,
  activities: EventNoteOutlined,
  marketing: CampaignOutlined,
  reports: AssessmentOutlined,
  integrations: ExtensionOutlined,
  usage: ReceiptLongOutlined,
  billing: RequestQuoteOutlined,
  settings: SettingsOutlined,
  "settings-workspace": CorporateFareOutlined,
  "settings-team": PeopleOutlined,
  "settings-roles": BadgeOutlined,
  "settings-api": KeyOutlined,
  "platform-home": AdminPanelSettingsOutlined,
  "platform-tenants": CorporateFareOutlined,
  "platform-packages": Inventory2Outlined,
  "platform-modules": ViewModuleOutlined,
  "platform-landing": CampaignOutlined,
  "platform-subscriptions": CardMembershipOutlined,
  "platform-invoices": RequestQuoteOutlined,
  "platform-gateways": AccountBalanceOutlined,
  "platform-lead-sources": KeyOutlined,
  "platform-telemetry": HistoryOutlined,
  "platform-settings": SettingsOutlined,
};

export function navIcon(id: string): SvgIconComponent {
  return navIcons[id] ?? SpaceDashboardOutlined;
}
