import type { Metadata } from "next";
import { AppLayout } from "@/components/layout/app-layout";
import { ProcessingView } from "@/features/datasets/processing-view";

export const metadata: Metadata = { title: "Processing dataset" };

export default async function ProcessingPage({ params }: { params: Promise<{ datasetId: string }> }) {
  const { datasetId } = await params;
  return (
    <AppLayout width="md">
      <ProcessingView datasetId={datasetId} />
    </AppLayout>
  );
}
