import { onDomReady } from "./imports/utils.js";

onDomReady(initDialogs);

export function initDialogs() {
  let modals = document.querySelectorAll(".modal-wrapper");

  modals.forEach((modal) => {
    modal
      .querySelector("button.modal-trigger")
      .addEventListener("click", (event) => {
        let target =
          "dialog#" +
          modal.querySelector("button.modal-trigger").dataset.target;
        modal.querySelector(target).showModal();
      });

    let close_buttons = modal.querySelectorAll(".close-modal-button");

    close_buttons.forEach((close_button) => {
      close_button.addEventListener("click", (event) => {
        modal.querySelector("dialog").close();
      });
    });

    document.addEventListener("keydown", (event) => {
      if (event.key.toLowerCase() === "escape") {
        modal.querySelector("dialog").close();
      }
    });
  });
}
