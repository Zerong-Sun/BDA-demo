const { candidates, statusClass, nodeTemplates } = window.BDA_DEMO_DATA;

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

window.addCustomNode = addCustomNode;

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
