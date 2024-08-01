import { onDomReady } from "../js/imports/utils.js";

onDomReady(initConfirmButtons);

export function initConfirmButtons(element) {
  let root = element || document;
  let confirm_buttons = root.querySelectorAll(".confirm-button");

  confirm_buttons.forEach((button) => initClickHandlers(button));
}

function initClickHandlers(button) {
  button.addEventListener("click", function (event) {
    const target = event.target.closest("dialog");

    editReportName(target);
  });
}

function editReportName(target) {
  const old_name_id = target.querySelector(".old-report-name").value;
  const reference_date = target.querySelector(".reference-date").value;
  const update_target_input = document.getElementById(old_name_id);
  const update_target_text = document.getElementById("text-" + old_name_id);

  let new_name = target.querySelector(".new-report-name").value;

  if (new_name) {
    if (reference_date) {
      new_name += " (" + reference_date + ")";
    }
    update_target_input.setAttribute("value", new_name);
    update_target_text.textContent = new_name;
  }
}
