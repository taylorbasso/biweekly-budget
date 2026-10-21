document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".essential-toggle").forEach((checkbox) => {
    checkbox.addEventListener("change", () => {
      fetch(checkbox.form.action, {
        method: "POST",
        body: new FormData(checkbox.form),
        redirect: "manual",
      });
    });
  });
});
