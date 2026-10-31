import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../services/api";
import { useNotice } from "../store/notice";
import type { Json } from "../types/api";

export function useGet<T = Json>(path: string | null, key?: unknown[]) {
  return useQuery<T>({ queryKey: key ?? [path], queryFn: () => http.get<T>(path!), enabled: path !== null });
}

/**
 * After ANY change, refetch every query: the backend re-analyses the whole profile (spec §57).
 * Pass `saved` to show a visible confirmation when the change has been kept.
 */
export function useAction<TBody = unknown, TRes = Json>(fn: (body: TBody) => Promise<TRes>, saved?: string) {
  const qc = useQueryClient();
  const { notify } = useNotice();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      qc.invalidateQueries();
      if (saved) notify(saved);
    },
  });
}
