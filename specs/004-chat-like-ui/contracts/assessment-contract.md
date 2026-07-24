# Assessment Contract

Assessment completion is represented by the existing review-attempt submit response.
The UI normalizes it to:

```ts
interface AssessmentResult {
  attemptId: string;
  milestoneKey: string;
  scorePercent: number;
  passed: boolean;
  achievementTier: "bronze" | "silver" | "gold";
  evidence: { questionIds: string[]; submittedAt: string };
}
```

The tier is derived from the shared score policy and rendered with text plus the medal
visual. On success, the client refetches the learning session and progress/roadmap
snapshot before notifying all route subscribers. On failure, the current attempt and
answers remain available for retry according to the existing review contract.
