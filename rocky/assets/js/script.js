import { onDomReady } from "../js/imports/utils.js";

onDomReady(initDialogs);

export function initDialogs() {
  let modal_components = document.querySelectorAll(".modal-wrapper");

  modal_components.forEach((modal) => {
    modal
      .querySelector("button.modal-trigger")
      .addEventListener("click", (event) => {
        let target =
          "dialog" + modal.querySelector("button.modal-trigger").dataset.target;
        modal.querySelector(target).showModal();
      });

    let dialog_element = modal.querySelector("dialog");

    dialog_element.addEventListener("click", (event) => {
      // event.target.nodeName === 'DIALOG' is needed to check if the ::backdrop is clicked.
      if (
        event.target.nodeName === "DIALOG" ||
        event.target.classList.contains("close-modal-button")
      ) {
        dialog_element.close();
      }
    });
  });
}
