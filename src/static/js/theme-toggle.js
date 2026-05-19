(function () {
  var root = document.documentElement;
  var storageKey = "stewardwell-theme";

  function getPreferredTheme() {
    var storedTheme = localStorage.getItem(storageKey);
    if (storedTheme === "light" || storedTheme === "dark") {
      return storedTheme;
    }
    var prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    return prefersDark ? "dark" : "light";
  }

  function setTheme(theme) {
    root.setAttribute("data-theme", theme);
    localStorage.setItem(storageKey, theme);
    var isDark = theme === "dark";

    // Support legacy floating button (public pages)
    var legacyBtn = document.getElementById("theme-toggle");
    if (legacyBtn) {
      var icon = legacyBtn.querySelector(".theme-toggle-icon");
      var label = legacyBtn.querySelector(".theme-toggle-label");
      legacyBtn.setAttribute("aria-pressed", String(isDark));
      if (icon) icon.textContent = isDark ? "\uD83C\uDF19" : "\u2600\uFE0F";
      if (label) label.textContent = isDark ? "Dark mode" : "Light mode";
      // New icon-only nav button: swap moon/sun SVG title
      if (!icon) legacyBtn.setAttribute("title", isDark ? "Switch to light mode" : "Switch to dark mode");
    }
  }

  function toggleTheme() {
    var currentTheme = root.getAttribute("data-theme") || "light";
    setTheme(currentTheme === "dark" ? "light" : "dark");
  }

  document.addEventListener("DOMContentLoaded", function () {
    setTheme(getPreferredTheme());
    var btn = document.getElementById("theme-toggle");
    if (btn) btn.addEventListener("click", toggleTheme);
  });
})();

