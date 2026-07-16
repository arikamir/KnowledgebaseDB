import { GuidanceForm } from "./GuidanceForm";
import { GuidanceResult } from "./GuidanceResult";
import { useGuidance } from "./useGuidance";

export function GuidancePage() {
  const guidance = useGuidance();
  return <><h1>Skill guidance</h1><GuidanceForm topic={guidance.topic} onTopicChange={guidance.setTopic} profile={guidance.profile} onProfileChange={guidance.setProfile} onSubmit={guidance.submit} persistence={guidance.snapshot} problem={guidance.problem} />{guidance.result && <GuidanceResult result={guidance.result} />}</>;
}
