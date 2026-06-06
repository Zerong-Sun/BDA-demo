window.BDA_DEMO_DATA = {
  candidates: [
    ["PD1Binder_c4361", "F2", 94, "0.6 nM", 92, "1.8 A", "High", "Validated", "Anchor"],
    ["PD1Binder_a0172", "F2", 91, "1.1 nM", 89, "2.1 A", "High", "Validated", "Order"],
    ["PD1Binder_b1923", "F5", 87, "2.4 nM", 84, "2.6 A", "Medium", "Validated", "Order"],
    ["PD1Binder_c7239", "F1", 82, "4.8 nM", 76, "3.8 A", "Low", "QC risk", "Hold"],
    ["PD1Binder_a6562", "F3", 80, "5.2 nM", 83, "2.9 A", "Medium", "Retest", "Retest"],
    ["PD1Binder_d4410", "F6", 77, "7.5 nM", 80, "2.7 A", "High", "Reserve", "Reserve"],
    ["PD1Binder_e2014", "F4", 74, "9.8 nM", 72, "3.1 A", "Medium", "Reserve", "Reserve"],
    ["PD1Binder_f1021", "F7", 71, "12 nM", 79, "2.5 A", "High", "Reserve", "Reserve"],
  ],
  statusClass: {
    Validated: "green",
    "QC risk": "amber",
    Retest: "amber",
    Reserve: "",
  },
  nodeTemplates: {
    rf: {
      icon: "wand-sparkles",
      title: "Backbone generation",
      body: "Explore PD-1 binder geometry with RFdiffusion",
    },
    mpnn: {
      icon: "dna",
      title: "Sequence design",
      body: "ProteinMPNN sequence search with scaffold diversity constraints",
    },
    af2: {
      icon: "scan-search",
      title: "Fold prediction",
      body: "AlphaFold2 evaluates complex confidence, interface pAE, and clashes",
    },
    rosetta: {
      icon: "activity",
      title: "Rosetta scoring",
      body: "Rosetta relax and interface scoring estimate energy, clashes, and geometry",
    },
    filter: {
      icon: "filter",
      title: "BDA filters",
      body: "Rank candidates by interface, solubility, aggregation, and expression risk",
    },
    lab: {
      icon: "flask-conical",
      title: "Wet-lab validation",
      body: "Queue expression, purification, BLI, SEC, and thermal-shift assays",
    },
  },
};
