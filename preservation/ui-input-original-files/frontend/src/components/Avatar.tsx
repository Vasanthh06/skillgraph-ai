import { useQuery } from "@tanstack/react-query";
import { API_URL, tokenStore } from "../services/api";

/** Photos are private: fetched with the bearer token and shown from a blob, never from a public URL. */
export default function Avatar({ name, src, size = 40 }: { name: string; src?: string | null; size?: number }) {
  const photo = useQuery({
    queryKey: ["photo", src],
    enabled: !!src,
    staleTime: Infinity,
    queryFn: async () => {
      const r = await fetch(`${API_URL}${src}`, { headers: { Authorization: `Bearer ${tokenStore.get() ?? ""}`, "X-Auth-Token": tokenStore.get() ?? "" } });
      if (!r.ok) throw new Error("no photo");
      return URL.createObjectURL(await r.blob());
    },
  });
  const initials = name.split(" ").filter(Boolean).slice(0, 2).map((p) => p[0]!.toUpperCase()).join("");
  if (photo.data) {
    return <img src={photo.data} alt="" width={size} height={size} className="rounded-full object-cover" style={{ width: size, height: size }} />;
  }
  return (
    <span aria-hidden className="inline-flex items-center justify-center rounded-full bg-route-tint font-display text-route-dark" style={{ width: size, height: size, fontSize: size * 0.38 }}>
      {initials}
    </span>
  );
}
