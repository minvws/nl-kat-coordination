import { onDomReady } from "../js/imports/utils.js";

onDomReady(initDialogs);

export function initDialogs(element) {
  let root = element || document;
  let modal_components = root.querySelectorAll(".modal-wrapper");

  modal_components.forEach((modal) => initDialog(modal));
}

export function initDialog(modal) {
  let input_elements = [];

  modal.querySelector(".modal-trigger").addEventListener("click", (event) => {
    // Get and clone input elements to be able to "reset" them on "cancel".
    input_elements = modal.querySelectorAll("input, textarea");

    // Clone nodeList input_elements to simple array, instead of making a pointer reference.
    input_elements.forEach((element) => {
      element.defaultvalue = element.value;
    });

    // Used ".closest" instead of ".parentNode" to make sure we stay flexible in terms of
    // HTML-structure when implementing the trigger.
    event.target.closest(".modal-wrapper").querySelector("dialog").showModal();
  });

  modal.querySelector("dialog").addEventListener("click", (event) => {
    // The actual handling (like posting) of the input values should be done when implementing the component.
    if (event.target.classList.contains("confirm-modal-button")) {
      if (input_elements) {
        // Closing is only allowed when the inputs are 'valid'.
        if (checkValidity(input_elements)) {
          event.target
            .closest(".modal-wrapper")
            .querySelector("dialog")
            .close();
        }
        return;
      }
    }
    // event.target.nodeName === 'DIALOG' is needed to check if the ::backdrop is clicked.
    if (
      event.target.classList.contains("close-modal-button") ||
      event.target.nodeName === "DIALOG"
    ) {
      // When canceling or closing using the 'x' remove the "error" styles.
      input_elements.forEach((element) => {
        element.classList.remove("error");
      });

      // When canceling or closing the modal, the inputs get reset to their initial value.
      input_elements.forEach((element) => {
        element.value = element.defaultvalue;
      });

      event.target.closest(".modal-wrapper").querySelector("dialog").close();
    }
  });
}

export function checkValidity(elements) {
  let valid = true;

  elements.forEach((element) => {
    if (!element.checkValidity()) {
      valid = false;
      element.classList.add("error");
    } else {
      element.classList.remove("error");
    }
  });

  return valid;
}
