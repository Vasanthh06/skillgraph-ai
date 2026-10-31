import ErrorBanner from "./FormError";

interface Props {
  count: number;                 // number of unsaved changes (0 = everything is saved)
  saving?: boolean;
  onSave: () => void;
  onDiscard: () => void;
  saveLabel?: string;
  error?: string | null;
}

/** Sticky Save / Discard bar. Nothing is applied to the user's profile until Save is pressed. */
export default function SaveBar({ count, saving = false, onSave, onDiscard, saveLabel = "Save changes", error }: Props) {
  const dirty = count > 0;
  return (
    <div className="sticky bottom-3 z-10 mt-8">
      <div
        role="status"
        aria-live="polite"
        className={`flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-white px-4 py-3 shadow-md ${dirty ? "border-signal" : "border-mist"}`}
      >
        {dirty ? (
          <>
            <span><b>{count} unsaved change{count > 1 ? "s" : ""}</b> <span className="text-sm text-ink-faint">Not applied to your profile yet</span></span>
            <span className="flex gap-2">
              <button type="button" className="btn-quiet" onClick={onDiscard} disabled={saving}>Discard</button>
              <button type="button" className="btn" onClick={onSave} disabled={saving}>{saving ? "Saving…" : saveLabel}</button>
            </span>
          </>
        ) : (
          <span className="text-ink-soft">✓ All changes saved</span>
        )}
      </div>
      {error && <div className="mt-2"><ErrorBanner message={error} /></div>}
    </div>
  );
}
