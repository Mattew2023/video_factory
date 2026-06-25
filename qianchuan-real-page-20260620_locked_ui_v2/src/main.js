import { renderDashboardSkeleton } from "./render/dashboard.js";

const DATA_URL = "./data/dashboard-data.json";

async function bootstrap() {
  const root = document.querySelector("#app");
  const response = await fetch(DATA_URL);
  const dashboardData = await response.json();

  renderDashboardSkeleton(root, dashboardData);
}

bootstrap().catch((error) => {
  console.error("Failed to load data/dashboard-data.json.", error);
});
