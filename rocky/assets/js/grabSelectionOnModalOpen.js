import { onDomReady } from "./imports/utils.js";
import {
  renderRenameSelection,
  renderDeleteSelection,
} from "./reportActionForms.js";

onDomReady(function () {
  openDialogFromUrl(getAnchor());
});

export function openDialogFromUrl(anchor) {
  // If ID is present in the URL on DomReady, open the dialog immediately.
  let id = window.location.hash.slice(1);

  if (id) {
    let modal = document.querySelector("#" + id);

    if (anchor == "rename-modal") {
      renderRenameSelection(modal, getSelection());
    }
    if (anchor == "delete-modal") {
      renderDeleteSelection(modal, getSelection());
    }
  }
}

export function getSelection() {
  let checkedItems = document.querySelectorAll(".report-checkbox:checked");
  return checkedItems;
}

addEventListener("hashchange", function () {
  openDialogFromUrl(getAnchor());
});

function getAnchor() {
  let currentUrl = document.URL;
  let urlParts = currentUrl.split("#");

  return urlParts.length > 1 ? urlParts[1] : null;
}
