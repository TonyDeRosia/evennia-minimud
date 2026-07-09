const INITIAL_API_ENDPOINTS = Object.freeze([
  "/api/settings/global",
]);

async function loadGlobalSettings(fetchImpl = fetch) {
  const response = await fetchImpl("/api/settings/global");
  if (!response.ok) {
    throw new Error(`Unable to load Smart MUD settings: ${response.status}`);
  }
  return response.json();
}

async function bootSmartMud() {
  const settings = await loadGlobalSettings();
  document.documentElement.dataset.theme = settings.theme || "dark";
  document.title = settings.app_name || "Smart MUD";
  return settings;
}

if (typeof window !== "undefined") {
  window.SmartMudApi = {
    INITIAL_API_ENDPOINTS,
    loadGlobalSettings,
    bootSmartMud,
  };

  window.addEventListener("DOMContentLoaded", () => {
    bootSmartMud().catch((error) => console.error(error));
  });
}

export { INITIAL_API_ENDPOINTS, loadGlobalSettings, bootSmartMud };
