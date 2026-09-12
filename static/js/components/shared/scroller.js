const btn = document.getElementById("scrollTopBtn");

window.addEventListener("scroll", () => {
  const scrollTop = window.scrollY;
  const docHeight = document.documentElement.scrollHeight - window.innerHeight;
  const percent = scrollTop / docHeight;

  let opacity = 0;

  if (percent <= 0.5) {
    // 0 → 50%  => 0 → 1
    opacity = percent / 0.5;
  } else {
    // 50% → 100% => stay 1
    opacity = 1;
  }

  btn.style.opacity = opacity;
  btn.style.pointerEvents = opacity > 0.05 ? "auto" : "none";
});

btn.addEventListener("click", () => {
  window.scrollTo({
    top: 0,
    behavior: "smooth"
  });
});