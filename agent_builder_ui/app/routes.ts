import { type RouteConfig, index, route } from "@react-router/dev/routes";

export default [
  index("routes/dashboard.tsx"),
  route("login", "routes/login.tsx"),
  route("projects", "routes/projects.tsx"),
  route("agents", "routes/agents.tsx"),
  route("agents/create", "routes/agents/create.tsx"),
  route("agents/:id", "routes/agents/$id.tsx"),
  route("agents/:id/edit", "routes/agents/$id.edit.tsx"),
  route("workflows", "routes/workflows.tsx"),
  route("workflows/create", "routes/workflows/create.tsx"),
  route("workflows/:id", "routes/workflows/$id.tsx"),
  route("workflows/:id/edit", "routes/workflows/create.tsx", { id: "workflow-edit" }),
  route("tools", "routes/tools.tsx"),
  route("credentials", "routes/credentials.tsx"),
  route("credentials/create", "routes/credentials/create.tsx"),
  route("credentials/:id/edit", "routes/credentials/$id.edit.tsx"),
] satisfies RouteConfig;
