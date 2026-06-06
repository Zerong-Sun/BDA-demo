const candidates = [
  ["RBDBinder_c4361", "F2", 94, "0.6 nM", 92, "1.8 A", "High", "Validated", "Anchor"],
  ["RBDBinder_a0172", "F2", 91, "1.1 nM", 89, "2.1 A", "High", "Validated", "Order"],
  ["RBDBinder_b1923", "F5", 87, "2.4 nM", 84, "2.6 A", "Medium", "Validated", "Order"],
  ["RBDBinder_c7239", "F1", 82, "4.8 nM", 76, "3.8 A", "Low", "QC risk", "Hold"],
  ["RBDBinder_a6562", "F3", 80, "5.2 nM", 83, "2.9 A", "Medium", "Retest", "Retest"],
  ["RBDBinder_d4410", "F6", 77, "7.5 nM", 80, "2.7 A", "High", "Reserve", "Reserve"],
  ["RBDBinder_e2014", "F4", 74, "9.8 nM", 72, "3.1 A", "Medium", "Reserve", "Reserve"],
  ["RBDBinder_f1021", "F7", 71, "12 nM", 79, "2.5 A", "High", "Reserve", "Reserve"],
];

const statusClass = {
  "Validated": "green",
  "QC risk": "amber",
  "Retest": "amber",
  "Reserve": "",
};

const nodeTemplates = {
  rf: {
    icon: "wand-sparkles",
    title: "Backbone generation",
    body: "Explore binder geometry with RFdiffusion",
  },
  mpnn: {
    icon: "dna",
    title: "Sequence design",
    body: "ProteinMPNN sequence search with diversity constraints",
  },
  af3: {
    icon: "scan-search",
    title: "Fold prediction",
    body: "AlphaFold3 evaluates complex structure and local confidence",
  },
  openmm: {
    icon: "activity",
    title: "MD stability",
    body: "OpenMM MD checks conformational drift and interface stability",
  },
  filter: {
    icon: "filter",
    title: "BDA filters",
    body: "Rank candidates by affinity, solubility, aggregation, and expression risk",
  },
  lab: {
    icon: "flask-conical",
    title: "Wet-lab validation",
    body: "Queue expression, purification, BLI/SPR, SEC, and thermal-shift assays",
  },
};

let selectedNodeTemplate = "rf";
let customNodeCount = 0;

function setRoute(route) {
  document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
  document.querySelector(`#view-${route}`)?.classList.add("active");

  document.querySelectorAll("[data-route]").forEach((el) => {
    el.classList.toggle("active", el.dataset.route === route && el.tagName === "A");
  });

  window.location.hash = route;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function renderCandidates() {
  const body = document.querySelector("#candidateRows");
  body.innerHTML = candidates.map((candidate) => {
    const [name, family, affinity, kd, plddt, mdDrift, expression, status, decision] = candidate;
    const pillClass = statusClass[status] || "";
    return `
      <tr>
        <td><strong>${name}</strong></td>
        <td>${family}</td>
        <td>${affinity}</td>
        <td>${kd}</td>
        <td>${plddt}</td>
        <td>${mdDrift}</td>
        <td>${expression}</td>
        <td><span class="pill ${pillClass}">${status}</span></td>
        <td>${decision}</td>
      </tr>
    `;
  }).join("");
}

function selectedMethods() {
  const methods = Array.from(document.querySelectorAll("[data-method]:checked")).map((item) => item.dataset.method);
  return methods.length ? methods : ["No method selected"];
}

function renderNodePreview() {
  const preview = document.querySelector("#nodePreview");
  if (!preview) return;
  const template = nodeTemplates[selectedNodeTemplate];
  preview.innerHTML = `
    <header><i data-lucide="${template.icon}"></i><span>${template.title}</span></header>
    <p>${template.body}</p>
    <footer><span class="node-port"></span>${selectedMethods().join(", ")}</footer>
  `;
  if (window.lucide) window.lucide.createIcons();
}

function addCustomNode() {
  const layer = document.querySelector("#customNodeLayer");
  if (!layer) return;
  const template = nodeTemplates[selectedNodeTemplate];
  const methods = selectedMethods().join(", ");
  const positions = [
    { left: 285, top: 70 },
    { left: 515, top: 70 },
    { left: 285, top: 470 },
    { left: 48, top: 250 },
  ];
  const position = positions[customNodeCount % positions.length];
  customNodeCount += 1;

  const node = document.createElement("article");
  node.className = "node custom-node";
  node.style.left = `${position.left}px`;
  node.style.top = `${position.top}px`;
  node.innerHTML = `
    <header><i data-lucide="${template.icon}"></i><span>${template.title}</span></header>
    <p>${template.body}</p>
    <footer><span class="node-port"></span>${methods}</footer>
  `;
  layer.appendChild(node);
  if (window.lucide) window.lucide.createIcons();
}

function wireActions() {
  document.querySelectorAll("[data-route]").forEach((el) => {
    el.addEventListener("click", (event) => {
      event.preventDefault();
      setRoute(el.dataset.route);
    });
  });

  document.querySelectorAll("[data-agent-action]").forEach((button) => {
    button.addEventListener("click", () => {
      const action = button.dataset.agentAction;
      document.querySelectorAll("[data-agent-action]").forEach((item) => {
        item.classList.toggle("active", item.dataset.agentAction === action);
      });
      document.querySelectorAll("[data-agent-view]").forEach((view) => {
        view.classList.toggle("active", view.dataset.agentView === action);
      });
    });
  });

  document.querySelector("#addNodeToggle")?.addEventListener("click", () => {
    document.querySelector("#nodeBuilder")?.classList.toggle("open");
  });

  document.querySelector("#closeNodeBuilder")?.addEventListener("click", () => {
    document.querySelector("#nodeBuilder")?.classList.remove("open");
  });

  document.querySelectorAll("[data-node-template]").forEach((button) => {
    button.addEventListener("click", () => {
      selectedNodeTemplate = button.dataset.nodeTemplate;
      document.querySelectorAll("[data-node-template]").forEach((item) => {
        item.classList.toggle("active", item.dataset.nodeTemplate === selectedNodeTemplate);
      });
      renderNodePreview();
    });
  });

  document.querySelectorAll("[data-method]").forEach((checkbox) => {
    checkbox.addEventListener("change", renderNodePreview);
  });

  document.querySelector("#addCustomNode")?.addEventListener("click", addCustomNode);

  document.querySelector("#toggleCopilot").addEventListener("click", () => {
    document.querySelector("#copilotPanel").classList.toggle("open");
  });

  document.querySelector("#runWorkflow").addEventListener("click", (event) => {
    const button = event.currentTarget;
    button.innerHTML = '<span class="spinner"></span> Running...';
    button.disabled = true;
    setTimeout(() => {
      button.innerHTML = '<i data-lucide="check"></i> Workflow completed';
      button.classList.remove("success");
      button.classList.add("primary");
      if (window.lucide) window.lucide.createIcons();
    }, 1300);
  });
}

renderCandidates();
wireActions();
renderNodePreview();
setRoute((window.location.hash || "#experiments").replace("#", ""));
if (window.lucide) window.lucide.createIcons();
