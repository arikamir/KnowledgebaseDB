import { ProgressForm } from "./ProgressForm";
import { ProgressReview } from "./ProgressReview";
import { useProgress } from "./useProgress";

export function ProgressPage() {
  const progress = useProgress();
  return <>
    <h1>Progress check-in</h1>
    {progress.notice && <p role="status">{progress.notice}</p>}
    <ProgressForm input={progress.input} onChange={progress.setInput} onSubmit={progress.submit} persistence={progress.snapshot} problem={progress.problem} />
    {progress.review && <ProgressReview review={progress.review} />}
  </>;
}
