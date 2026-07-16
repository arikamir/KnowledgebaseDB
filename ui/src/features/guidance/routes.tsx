import { registerRoute } from "../../app/route-registry";
import { GuidancePage } from "./GuidancePage";

export const guidanceRoute = { id: "guidance", path: "/guidance", navigationLabel: "Guidance", element: <GuidancePage /> };
registerRoute(guidanceRoute);
