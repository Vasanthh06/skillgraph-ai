import { useNavigation } from "../store/navigation";
export default function HistoryControls() {
  const {back, forward, canBack, canForward, fallback} = useNavigation();
  return <nav aria-label="Page history" className="history-controls">
    <button type="button" aria-label="Back" title={fallback ? "No previous in-app page. Return to dashboard" : "Previous application page"} disabled={!canBack && !fallback} onClick={back}><span aria-hidden="true">←</span><span>Back</span></button>
    <button type="button" aria-label="Forward" title="Next application page" disabled={!canForward} onClick={forward}><span>Forward</span><span aria-hidden="true">→</span></button>
  </nav>;
}
