import { useEffect } from "react";
import type { ProgressReview as ProgressReviewValue } from "../../contracts/bff-api";

function words(value: string): string {
  return value.replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase());
}

export function ProgressReview({ review }: { review: ProgressReviewValue }) {
  useEffect(() => { performance.mark("progress.result.accessible-render-committed"); }, [review]);
  return <section aria-labelledby="progress-review-heading">
    <h2 id="progress-review-heading">Progress review</h2>
    <p><strong>Current status:</strong> {words(review.currentStatus)}</p>
    <section aria-labelledby="progress-gaps-heading">
      <h3 id="progress-gaps-heading">Current gaps</h3>
      {review.gaps.length ? <ul>{review.gaps.map((gap) => <li key={gap}>{gap}</li>)}</ul> : <p>No current gaps.</p>}
    </section>
    <section aria-labelledby="progress-milestones-heading">
      <h3 id="progress-milestones-heading">Milestones</h3>
      <ul>{review.milestones.map((milestone) => <li key={milestone.milestoneKey}>{milestone.title} — {words(milestone.completionState)}</li>)}</ul>
    </section>
    <section aria-labelledby="progress-next-heading">
      <h3 id="progress-next-heading">Recommended next action</h3>
      <p><strong>{review.nextAction.title}</strong></p>
      <p>{review.nextAction.reason}</p>
    </section>
  </section>;
}
