export type LearnerStatus = "loading" | "ready" | "empty" | "unavailable" | "error";
export type DeliveryState = "ready" | "pending" | "delivered" | "failed";
export type CompletionState = "pending" | "in_progress" | "completed";
export type AchievementTier = "bronze" | "silver" | "gold";

export interface UiError { code: string; message: string; retryable: boolean; fieldErrors?: Record<string, string[]>; }
export interface AssessmentEvidence { assessmentId: string; milestoneKey: string; scorePercent: number; passed: boolean; achievementTier: AchievementTier | null; recordedAt: string; questionIds?: string[]; }
export interface LabReference { id: string; provider: string; objective: string; destinationUrl: string; availabilityStatus: "active" | "unavailable" | "retired"; }
export interface MilestoneSnapshot { milestoneKey: string; ordinal: number; title: string; completionState: CompletionState; scorePercent: number | null; passed: boolean | null; achievementTier: AchievementTier | null; concreteNextAction?: string; evidence: AssessmentEvidence[]; }
export interface CurrentTopic { milestoneKey: string; title: string; completionState: CompletionState; concreteNextAction?: string; }
export interface NextAction { kind: "retry_material" | "resume_session" | "continue_milestone" | "review_roadmap"; title: string; reason: string; target: string; }
export interface AssistantContent { topicSummary: string; currentLevelFit: string; practicalNextAction: string; suggestions: string[]; commonPitfalls: string[]; relatedTopics: string[]; labReferences: LabReference[]; }
export interface Message { id: string; role: "user" | "assistant"; text: string; createdAt: string; assistantContent?: AssistantContent; }
export interface Conversation { messages: Message[]; draft: string; deliveryState: DeliveryState; failure: UiError | null; }
export interface LearnerState { roadmap: unknown | null; conversation: Conversation; currentTopic: CurrentTopic | null; nextAction: NextAction | null; milestones: MilestoneSnapshot[]; lastUpdatedAt: string | null; status: LearnerStatus; error: UiError | null; authEpoch: number; }
