"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { reportService } from "@/services/report.service";
import { getErrorMessage } from "@/services/api-client";
import { toast } from "@/stores/toast.store";
import type { ReportConfig } from "@/types/report";

export function useReportPreview(datasetId: string, config: ReportConfig) {
  return useQuery({
    queryKey: ["reports", datasetId, "preview", config.title, config.datePreset, [...config.metrics].sort().join(",")],
    queryFn: () => reportService.preview(datasetId, config),
    enabled: config.metrics.length > 0,
  });
}

export function useReportHistory(datasetId: string) {
  return useQuery({ queryKey: ["reports", datasetId, "history"], queryFn: () => reportService.list(datasetId) });
}

export function useCreateReport(datasetId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (config: ReportConfig) => reportService.create(datasetId, config),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["reports", datasetId, "history"] }),
    onError: (error) => toast.error("Could not generate report", getErrorMessage(error)),
  });
}
