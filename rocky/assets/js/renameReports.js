import { onDomReady } from "../js/imports/utils.js";

onDomReady(initRenameReports);

function initRenameReports() {
  initResetButtons();

  const table = document.getElementById("report-name-table");
  if (!table) return;

  table.addEventListener("click", function (event) {
    if (!event.target.matches(".reset-button")) return;
    event.stopPropagation();
    const button = event.target;
    const input = button.closest("tr")?.querySelector(".name-input");
    if (!input) return;
    input.value = input.defaultvalue;
    button.classList.add("hidden");
  });

  table.addEventListener("change", function (event) {
    if (!event.target.matches(".name-input")) return;
    event.stopPropagation();
    const input = event.target;
    const button = input.closest("tr")?.querySelector(".reset-button");
    if (!button) return;
    if (input.defaultValue === input.value) {
      button.classList.add("hidden");
    } else {
      button.classList.remove("hidden");
    }
  });
}

function initResetButtons() {
  const resetButtons = document.querySelectorAll(".reset-button");

  resetButtons.forEach((button) => {
    button.classList.add("hidden");

    let input = button.closest("tr")?.querySelector(".name-input");
    if (!input) return;

    input.defaultvalue = input.value;
  });
}
