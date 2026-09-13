import type { SidebarsConfig } from "@docusaurus/plugin-content-docs";

const sidebars: SidebarsConfig = {
  tutorialSidebar: [
    {
      type: "category",
      label: "Getting Started",
      items: [
        "getting-started/overview",
        "getting-started/requirements",
        "getting-started/installation",
        "getting-started/quickstart",
      ],
    },
    {
      type: "category",
      label: "Configuration",
      items: [
        "configuration/models",
        "configuration/environment",
        "configuration/storage",
      ],
    },
    {
      type: "category",
      label: "Usage",
      items: [
        "usage/chat",
        "usage/document-retrieval",
        "usage/troubleshooting",
      ],
    },
    {
      type: "category",
      label: "Architecture",
      items: ["architecture/overview", "architecture/components"],
    },
    {
      type: "category",
      label: "Development",
      items: ["development/contributing", "development/testing"],
    },
  ],
};

export default sidebars;
