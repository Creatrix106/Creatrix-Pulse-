import { redirect } from "next/navigation";
import { siteConfig } from "@/config/site";

/** /dashboard has no content of its own – open the default dataset. */
export default function DashboardIndexPage() {
  redirect(`/dashboard/${siteConfig.defaultDatasetId}`);
}
