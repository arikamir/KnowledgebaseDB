import { registerRoute } from "../../app/route-registry";
import { ProgressPage } from "./ProgressPage";

export const progressRoute = { id: "progress", path: "/progress", navigationLabel: "Progress", element: <ProgressPage /> };
registerRoute(progressRoute);
