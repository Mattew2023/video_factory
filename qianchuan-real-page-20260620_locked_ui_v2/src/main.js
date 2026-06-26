import { renderDashboardSkeleton } from "./render/dashboard.js";

const DATA_URL = "./data/dashboard-data.json";
const DESIGN_WIDTH = 2560;
const DESIGN_HEIGHT = 1348;

function getPreviewScale() {
  const params = new URLSearchParams(window.location.search);
  const scaleParam = params.get("previewScale");

  if (scaleParam === "fit") {
    return Math.min(window.innerWidth / DESIGN_WIDTH, window.innerHeight / DESIGN_HEIGHT, 1);
  }

  const numericScale = Number(scaleParam);

  if (Number.isFinite(numericScale) && numericScale > 0 && numericScale <= 1) {
    return numericScale;
  }

  return 1;
}

function applyPreviewScale(root) {
  const scale = getPreviewScale();

  root.style.setProperty("--preview-scale", String(scale));
  root.style.setProperty("--scaled-design-width", `${DESIGN_WIDTH * scale}px`);
  root.style.setProperty("--scaled-design-height", `${DESIGN_HEIGHT * scale}px`);
}

async function bootstrap() {
  const root = document.querySelector("#app");
  applyPreviewScale(root);

  const response = await fetch(DATA_URL);
  const dashboardData = await response.json();

  renderDashboardSkeleton(root, dashboardData);

  window.addEventListener("resize", () => applyPreviewScale(root));
}

bootstrap().catch((error) => {
  console.error("Failed to load data/dashboard-data.json.", error);
});
