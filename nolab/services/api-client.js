window.BDA_API = {
  mode: "api-gateway",
  baseUrl: "http://127.0.0.1:8100",
  endpoints: {
    projects: "/projects",
    workflowRuns: "/workflow-runs",
    candidates: "/candidates",
    computeNodes: "/compute-nodes",
    modelPlugins: "/model-plugins",
    methodPlugins: "/method-plugins",
  },
  async request(path, options = {}) {
    const response = await fetch(`${this.baseUrl}${path}`, {
      headers: { "content-type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    const payload = await response.json();
    if (!response.ok) {
      const error = new Error(payload.message || payload.detail || "BDA API request failed");
      error.payload = payload;
      throw error;
    }
    return payload.data;
  },
  listProjects() {
    return this.request("/projects");
  },
  listCandidates(projectId = "proj_pd1_0423") {
    return this.request(`/projects/${projectId}/candidates`);
  },
  listWorkflowNodes(workflowRunId = "run_pd1_round1") {
    return this.request(`/workflow-runs/${workflowRunId}/nodes`);
  },
  listComputeNodes() {
    return this.request("/compute-nodes");
  },
  listModelPlugins() {
    return this.request("/model-plugins");
  },
};
