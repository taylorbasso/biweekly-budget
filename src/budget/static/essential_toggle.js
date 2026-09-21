document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".essential-toggle").forEach((checkbox) => {
    checkbox.addEventListener("change", () => {
      fetch(checkbox.form.action, { method: "POST", redirect: "manual" });
    });
  });
});
