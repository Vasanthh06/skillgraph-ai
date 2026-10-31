import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../services/api";
import type { ProfileUpdate } from "../types";

export function useProfile() {
  return useQuery({ queryKey: ["profile"], queryFn: api.profile });
}

export function useUpdateProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (d: ProfileUpdate) => api.updateProfile(d),
    onSuccess: (p) => qc.setQueryData(["profile"], p),
  });
}

export function useUploadPhoto() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (f: File) => api.uploadPhoto(f),
    onSuccess: (p) => { qc.setQueryData(["profile"], p); qc.invalidateQueries({ queryKey: ["photo"] }); },
  });
}
