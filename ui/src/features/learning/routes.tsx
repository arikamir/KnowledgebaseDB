import { registerRoute } from "../../app/route-registry";
import { LearningPage } from "./LearningPage";

export const learningRoute = { id: "learning", path: "/learning/:id", navigationLabel: "Learning", element: <LearningPage /> };
registerRoute(learningRoute);
