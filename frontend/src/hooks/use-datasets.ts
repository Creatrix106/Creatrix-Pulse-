"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { datasetService } from "@/services/dataset.service";
import { getErrorMessage, isApiError } from "@/services/api-client";
import { toast } from "@/stores/toast.store";
import type { UploadRequest } from "@/types/dataset";

export const datasetKeys = {
  all: ["datasets"] as const,
  detail: (id: string) => ["datasets", id] as const,
  processing: (id: string) => ["datasets", id, "processing"] as const,
};

export function useDatasets() {
  return useQuery({ queryKey: datasetKeys.all, queryFn: () => datasetService.list() });
}

export function useDataset(id: string) {
  return useQuery({
    queryKey: datasetKeys.detail(id),
    queryFn: () => datasetService.get(id),
    enabled: Boolean(id),
    retry: (count, error) => !(isApiError(error) && error.status < 500 && error.status > 0) && count < 2,
  });
}

/** Polls processing status until the dataset is ready or has failed. */
export function useProcessingStatus(id: string) {
  return useQuery({
    queryKey: datasetKeys.processing(id),
    queryFn: () => datasetService.getProcessingStatus(id),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "ready" || status === "failed" ? false : 1200;
    },
  });
}

export function useDeleteDataset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => datasetService.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: datasetKeys.all });
      toast.success("Dataset deleted");
    },
    onError: (error) => toast.error("Could not delete dataset", getErrorMessage(error)),
  });
}

export function useUploadDataset(onProgress?: (percent: number) => void) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (request: UploadRequest) => datasetService.upload(request, onProgress),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: datasetKeys.all }),
  });
}
