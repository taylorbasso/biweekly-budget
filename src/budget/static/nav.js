document.addEventListener("DOMContentLoaded", () => {
  const nav = document.querySelector("nav");
  const toggle = nav.querySelector(".nav-toggle");

  const setOpen = (open) => {
    nav.classList.toggle("open", open);
    toggle.setAttribute("aria-expanded", String(open));
  };

  toggle.addEventListener("click", () => setOpen(!nav.classList.contains("open")));

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && nav.classList.contains("open")) {
      setOpen(false);
      toggle.focus();
    }
  });

  document.addEventListener("click", (event) => {
    if (!nav.contains(event.target)) {
      setOpen(false);
    }
  });
});
