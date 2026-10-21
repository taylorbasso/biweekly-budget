// A <select data-toggles-fields> shows only the fields in its form whose
// data-show-for matches its value; hidden fields are disabled so they aren't
// submitted. Used by the expense form (recurrence) and debt form (type).
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("select[data-toggles-fields]").forEach((select) => {
    const fields = select.form.querySelectorAll("[data-show-for]");

    function update() {
      fields.forEach((field) => {
        const matches = field.dataset.showFor === select.value;
        field.hidden = !matches;
        field.querySelectorAll("input, select").forEach((input) => {
          input.disabled = !matches;
        });
      });
    }

    select.addEventListener("change", update);
    update();
  });
});
