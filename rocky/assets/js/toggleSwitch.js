import { onDomReady } from "../js/imports/utils.js";

onDomReady(initToggle);

function initToggle() {
  document.querySelector(".manual-selection-form").classList.add("hidden");
  let switch_button_list = document.getElementsByClassName(
    "toggle-switch-button",
  );

  for (let i = 0; i < switch_button_list.length; i++) {
    switch_button_list[i].addEventListener("click", (event) => {
      toggle();
    });
  }
}
function toggle() {
  let manual_form = document.querySelector(".manual-selection-form");
  let live_set_form = document.querySelector(".live-set-form");

  if (manual_form.classList.contains("hidden")) {
    document
      .querySelector(".manual-selection-button")
      .parentElement.setAttribute("aria-current", "true");
    document
      .querySelector(".live-set-button")
      .parentElement.setAttribute("aria-current", "false");
  }

  if (live_set_form.classList.contains("hidden")) {
    document
      .querySelector(".live-set-button")
      .parentElement.setAttribute("aria-current", "true");
    document
      .querySelector(".manual-selection-button")
      .parentElement.setAttribute("aria-current", "false");
  }

  manual_form.classList.toggle("hidden");
  live_set_form.classList.toggle("hidden");
}
