const html = document.documentElement;
const toggleLink = document.getElementById("themeToggle");

// Apply theme + update text
function setTheme(theme) {
  html.setAttribute("data-bs-theme", theme);

  toggleLink.textContent = theme === "dark"
    ? "Light Theme"
    : "Dark Theme";

  // Save to session
  sessionStorage.setItem("theme", theme);
}

// On load: check saved theme first
const savedTheme = sessionStorage.getItem("theme");

if (savedTheme) {
  setTheme(savedTheme);
} else {
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  setTheme(prefersDark ? "dark" : "light");
}

// Toggle on click
toggleLink.addEventListener("click", function(e) {
  e.preventDefault();
  const current = html.getAttribute("data-bs-theme");
  setTheme(current === "dark" ? "light" : "dark");
});