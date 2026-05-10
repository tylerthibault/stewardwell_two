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

    var toggleButton = document.getElementById("theme-toggle");
    if (!toggleButton) {
      return;
    }

    var icon = toggleButton.querySelector(".theme-toggle-icon");
    var label = toggleButton.querySelector(".theme-toggle-label");

    var isDark = theme === "dark";
    toggleButton.setAttribute("aria-pressed", String(isDark));

    if (icon) {
      icon.textContent = isDark ? "🌙" : "☀️";
    }
    if (label) {
      label.textContent = isDark ? "Dark mode" : "Light mode";
    }
  }

  function toggleTheme() {
    var currentTheme = root.getAttribute("data-theme") || "light";
    var nextTheme = currentTheme === "dark" ? "light" : "dark";
    setTheme(nextTheme);
  }

  document.addEventListener("DOMContentLoaded", function () {
    setTheme(getPreferredTheme());

    var toggleButton = document.getElementById("theme-toggle");
    if (toggleButton) {
      toggleButton.addEventListener("click", toggleTheme);
    }
  });
})();
