import { crmApi } from "@/services/domainApi";
import type { Contact, Deal, Lead } from "@/types/domain";

function domainFromWebsite(website: string) {
  const raw = website.trim();
  if (!raw) return "";
  try {
    return new URL(raw.startsWith("http") ? raw : `https://${raw}`).hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
}

function contactFirstName(lead: Lead) {
  if (lead.email) return lead.email.split("@")[0];
  return lead.company_name || "Contact";
}

async function ensureContact(companyId: string, lead: Lead): Promise<Contact | null> {
  if (!lead.email && !lead.phone) return null;
  const existing = (await crmApi.contactsAll({ company: companyId })).find(
    (item) =>
      (lead.email && item.email && item.email.toLowerCase() === lead.email.toLowerCase()) ||
      (lead.phone && item.phone && item.phone === lead.phone),
  );
  if (existing) return existing;
  return crmApi.createContact({
    company: companyId,
    first_name: contactFirstName(lead),
    last_name: "",
    email: lead.email || "",
    phone: lead.phone || "",
  });
}

export async function promoteLeadToCrm(lead: Lead): Promise<Deal> {
  const pipelines = await crmApi.pipelines();
  const pipeline = pipelines.find((item) => item.is_default) ?? pipelines[0];
  const stage = [...(pipeline?.stages ?? [])].sort((left, right) => left.order - right.order)[0];
  if (!pipeline || !stage) {
    throw new Error("No CRM pipeline is available in this workspace.");
  }
  const domain = domainFromWebsite(lead.website);
  const companies = await crmApi.companiesAll({ search: lead.company_name });
  const existingCompany = companies.find(
    (item) => (domain && item.domain === domain) || item.name.toLowerCase() === lead.company_name.toLowerCase(),
  );
  const company =
    existingCompany ??
    (await crmApi.createCompany({
      name: lead.company_name,
      domain,
      industry: lead.industry,
      location: lead.location,
      phone: lead.phone,
      email: lead.email,
      notes: lead.description || lead.notes || "",
    }));
  const contact = await ensureContact(company.id, lead);
  const existingDeal = (await crmApi.dealsAll({ company: company.id })).find((item) => item.lead === lead.id);
  const deal =
    existingDeal != null
      ? await crmApi.updateDeal(existingDeal.id, {
          lead: lead.id,
          ...(contact && !existingDeal.contact ? { contact: contact.id } : {}),
        })
      : await crmApi.createDeal({
          pipeline: pipeline.id,
          stage: stage.id,
          company: company.id,
          name: lead.company_name,
          amount: "0",
          currency: "PKR",
          lead: lead.id,
          ...(contact ? { contact: contact.id } : {}),
        });
  const notes = (lead.notes || lead.description || "").trim();
  if (notes && !existingDeal) {
    await crmApi.createActivity({
      title: "Lead notes",
      kind: "note",
      body: notes,
      company: company.id,
      deal: deal.id,
      ...(contact ? { contact: contact.id } : {}),
    });
  }
  return deal;
}
