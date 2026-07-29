document.addEventListener("DOMContentLoaded", () => {
  const select = document.getElementById("recurrence-type");
  if (!select) return;

  const groups = document.querySelectorAll("[data-recurrence-for]");

  function update() {
    const recurrenceType = select.value;
    groups.forEach((group) => {
      const matches = group.dataset.recurrenceFor === recurrenceType;
      group.hidden = !matches;
      group.querySelectorAll("input, select").forEach((field) => {
        field.disabled = !matches;
      });
    });
  }

  select.addEventListener("change", update);
  update();
});
