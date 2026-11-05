import type { Metadata } from "next";
import { AppLayout } from "@/components/layout/app-layout";
import { UploadView } from "@/features/datasets/upload-view";

export const metadata: Metadata = { title: "Upload dataset" };

export default async function UploadPage({ searchParams }: { searchParams: Promise<{ replace?: string }> }) {
  const { replace } = await searchParams;
  return (
    <AppLayout width="lg">
      <UploadView replaceDatasetId={replace} />
    </AppLayout>
  );
}
