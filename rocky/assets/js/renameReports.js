import { onDomReady } from "../js/imports/utils.js";

onDomReady(initResetButtons);

function initResetButtons() {
  const resetButtons = document.querySelectorAll(".reset-button");

  resetButtons.forEach((button) => {
    button.classList.add("hidden");

    let input = button.closest("tr").querySelector(".name-input");

    input.defaultvalue = input.value;

    button.addEventListener("click", function (event) {
      input.value = input.defaultvalue;
      button.classList.add("hidden");
    });
  });

  watchInputChanges();
}

function watchInputChanges() {
  const nameInputs = document.querySelectorAll(".name-input");

  nameInputs.forEach((input) => {
    input.addEventListener("change", function (event) {
      let button = input.closest("tr").querySelector(".reset-button");

      if (input.defaultvalue === input.value) {
        button.classList.add("hidden");
      } else {
        button.classList.remove("hidden");
      }
    });
  });
}
