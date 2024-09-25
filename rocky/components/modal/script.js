import { onDomReady } from "../js/imports/utils.js";

onDomReady(initDialogs);

export function initDialogs(element) {
  let root = element || document;
  let modal_components = root.querySelectorAll(".modal-wrapper");

  modal_components.forEach((modal) => initDialog(modal));
}

export function initDialog(modal) {
  let id = window.location.toString().split("#")[1];
  let dialog_element = modal.querySelector("dialog");
  if (!dialog_element) return;

  let trigger = document.querySelector(
    "[data-modal-id='" + dialog_element.id + "']",
  );
  if (!trigger) return;

  // If ID is present in the URL on init, open the dialog immediately.
  if (id) {
    ShowModalBasedOnAnchor(id);
  }

  // Check if trigger element is <a>, if not, on click,
  // alter the URL to open the dialog using the onhaschange event.
  if (trigger.nodeName !== "A") {
    trigger.addEventListener("click", (event) => {
      let url = window.location.toString();
      window.location = url + "#" + dialog_element.id;
    });
  }

  modal.querySelector("dialog").addEventListener("click", (event) => {
    // The actual handling (like posting) of the input values should be done when implementing the component.
    // event.target.nodeName === 'DIALOG' is needed to check if the ::backdrop is clicked.
    if (
      event.target.classList.contains("confirm-modal-button") ||
      event.target.classList.contains("close-modal-button") ||
      event.target.nodeName === "DIALOG"
    ) {
      event.target.closest(".modal-wrapper").querySelector("dialog").close();
    }
  });

  modal.querySelector("dialog").addEventListener("close", (event) => {
    removeDialogAnchor();
  });
}

export function removeDialogAnchor() {
  // Remove the anchor from the URL when closing the modal
  let baseUrl = window.location.toString().split("#")[0];
  window.history.pushState("", "Base URL", baseUrl);
}

export function ShowModalBasedOnAnchor(id) {
  if (id && document.querySelector("#" + id).nodeName === "DIALOG") {
    // Show modal, selected by ID
    document.querySelector("#" + id).showModal();
  }
}

window.onhashchange = function () {
  let id = window.location.toString().split("#")[1];
  ShowModalBasedOnAnchor(id);
};
