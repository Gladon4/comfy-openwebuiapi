import { app } from "../../../scripts/app.js";

app.registerExtension({
  name: "comfy-openwebui.dynamic_model-display",

  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "Generate") return;

    const origOnCreated = nodeType.prototype.onNodeCreated;
    const origConnectionsChange = nodeType.prototype.onConnectionsChange;

    nodeType.prototype.onNodeCreated = function () {
      if (origOnCreated) origOnCreated.apply(this, arguments);

      // find model widget
      this.modelWidget = this.widgets.find((w) => w.name === "model");

      const index = this.widgets.findIndex((w) => w.name === "model");

      if (index !== -1) {
        // remove original string widget
        this.widgets.splice(index, 1);

        // create real dropdown (combo)
        this.modelWidget = this.addWidget("combo", "model", "", () => {}, {
          values: [],
        });
      }
    };

    nodeType.prototype.onConnectionsChange = async function () {
      if (origConnectionsChange) {
        origConnectionsChange.apply(this, arguments);
      }

      function findConnectionNode(node) {
        let current = node.getInputNode(0);

        while (current) {
          // if this node has the widgets, it's your connection node
          if (current.widgets) {
            const names = current.widgets.map((w) => w.name);

            if (
              names.includes("ip") &&
              names.includes("port") &&
              names.includes("api_token")
            ) {
              return current;
            }
          }

          current = current.getInputNode(0);
        }

        return null;
      }

      const inputNode = findConnectionNode(this);
      if (!inputNode) {
        console.warn("No connection node found");
        return;
      }

      // get values from connection node widgets
      const ipWidget = inputNode.widgets.find((w) => w.name === "ip");
      const portWidget = inputNode.widgets.find((w) => w.name === "port");
      const tokenWidget = inputNode.widgets.find((w) => w.name === "api_token");

      if (!ipWidget || !portWidget || !tokenWidget) return;

      const ip = ipWidget.value;
      const port = portWidget.value;
      const token = tokenWidget.value;

      try {
        const res = await fetch(
          `/comfy-openwebui/models?ip=${ip}&port=${port}&token=${token}`,
        );

        const models = await res.json();

        if (!Array.isArray(models)) return;

        const previousValue = this.modelWidget.value;

        this.modelWidget.options.values = models;

        if (models.includes(previousValue)) {
          this.modelWidget.value = previousValue;
        } else {
          this.modelWidget.value = models[0];
        }

        this.setDirtyCanvas(true, true);
      } catch (err) {
        console.error("Failed to fetch models:", err);
      }
    };
  },
});
