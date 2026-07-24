# UI State Contract

The shared learner-state provider exposes a read-only snapshot and commands:

```ts
interface LearnerStateContext {
  state: LearnerState;
  refresh(): Promise<void>;
  publishAssessment(evidence: AssessmentEvidence): Promise<void>;
  publishProgressReview(review: ProgressReview): Promise<void>;
  invalidate(reason: "auth-epoch" | "manual"): void;
}
```

Rules:

1. Commands call BFF operations only; the browser never calls core APIs.
2. A command publishes only validated, normalized DTOs.
3. Subscribers see either the previous complete snapshot or the next complete snapshot;
   partial milestone arrays are not published as ready state.
4. `invalidate("auth-epoch")` clears user-specific state and drafts that contain
   protected context, while the UI shows a sign-in/recovery action.
5. Mock mode imports the same fixture used by every route and is never enabled by
   production builds.
