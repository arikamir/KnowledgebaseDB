export function CompletionPanel({ result, onRetry }: { result: Record<string, unknown>; onRetry: () => Promise<void> }) {
  const passed = result.passed === true;
  return <section aria-labelledby="completion-title"><h2 id="completion-title">{passed ? "Learning session complete" : "Review missed concepts"}</h2><p>{passed ? "You passed the review and completed this milestone." : "Study the missed concepts, then begin a new full attempt."}</p><p>Score: {String(result.scorePercent ?? 0)}%</p>{!passed && <button onClick={() => void onRetry()}>Begin fresh full attempt</button>}</section>;
}
