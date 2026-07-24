import { registerRoute } from "../../app/route-registry";
import { RoadmapPage } from "./RoadmapPage";

export const roadmapRoute = { id: "roadmap", path: "/roadmaps", navigationLabel: "Roadmap", element: <RoadmapPage /> };
registerRoute(roadmapRoute);
