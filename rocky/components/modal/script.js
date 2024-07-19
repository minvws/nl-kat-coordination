import { onDomReady } from "../js/imports/utils.js";

onDomReady(initDialogs);

export function initDialogs(element) {
  let root = element || document;
  let modal_components = root.querySelectorAll(".modal-wrapper");

  modal_components.forEach((modal) => initDialog(modal));
}

export function initDialog(modal) {
  modal.querySelector(".modal-trigger").addEventListener("click", (event) => {
    // Used ".closest" instead of ".parentNode" to make sure we stay flexible in terms of
    // HTML-structure when implementing the trigger.
    event.target.closest(".modal-wrapper").querySelector("dialog").showModal();
  });

  modal.querySelector("dialog").addEventListener("click", (event) => {
    // event.target.nodeName === 'DIALOG' is needed to check if the ::backdrop is clicked.
    if (
      event.target.nodeName === "DIALOG" ||
      event.target.classList.contains("close-modal-button")
    ) {
      event.target.closest(".modal-wrapper").querySelector("dialog").close();
    }
  });
}
