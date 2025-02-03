function toggleElements(value) {
  const intervalNumber = document.querySelector(
    "label[for='id_interval_number']",
  ).parentElement;
  const intervalFrequency = document.querySelector(
    "label[for='id_interval_frequency']",
  ).parentElement;
  const runOn = document.querySelector("label[for='id_run_on']").parentElement;

  if (value === "interval") {
    intervalNumber.classList.remove("hidden-input");
    intervalFrequency.classList.remove("hidden-input");
    runOn.classList.add("hidden-input");
  } else if (value === "run_on") {
    intervalNumber.classList.add("hidden-input");
    intervalFrequency.classList.add("hidden-input");
    runOn.classList.remove("hidden-input");
  } else {
    intervalNumber.classList.add("hidden-input");
    intervalFrequency.classList.add("hidden-input");
    runOn.classList.add("hidden-input");
  }
}

document.addEventListener("DOMContentLoaded", function () {
  const radioButtons = document.querySelectorAll(".radio-choice");
  const selectedRadio = Array.from(radioButtons).find((radio) => radio.checked);

  toggleElements(selectedRadio ? selectedRadio.value : null);

  radioButtons.forEach(function (radio) {
    radio.addEventListener("change", function () {
      toggleElements(radio.value);
    });
  });
});
