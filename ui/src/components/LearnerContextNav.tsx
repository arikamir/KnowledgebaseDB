import { useLearnerState } from "../app/learner-state-context";
export function LearnerContextNav() { const { state } = useLearnerState(); return <nav className="learner-context-nav" aria-label="Learning context">{state.currentTopic && <span className="active-topic" aria-label={`Current topic: ${state.currentTopic.title}`}>Current topic: {state.currentTopic.title}</span>}</nav>; }
