function togglePlugins(containerClass) {
  const container = document.querySelector("."+containerClass);
  const button = container.querySelector("#more-suggested-plugins");
  const checkbox = document.getElementById("checkbox-for-enabled-optional-plugins");


  // Toggle "overflow" when amount of plugins exceed 4 (We only show 1 row containing 4 items, initially)
  function updateVisibility() {
    container.classList.toggle("hide-overflow");
    setButtonAmountText();
  }

  function setButtonAmountText() {
    const amountOfPlugins = container.getElementsByClassName("plugin").length;
    const amountOfDisabledPlugins = container.getElementsByClassName("plugin-is-disabled").length;
    let baseText = "";

    // Determine if the button text should be "Show" or "Hide"
    if(container.classList.contains("hide-overflow")) {
      baseText = button.dataset.showText;
    } else {
      baseText = button.dataset.hideText;
    }

    // Determine amount of "to be shown" plugins. Hide button if amount !> 0
    if(checkbox.checked) {
      if((amountOfPlugins - 4 > 0)) {
        button.classList.remove("hidden");
        button.innerHTML = `${baseText} (${amountOfPlugins - 4})`;
      } else {
        button.classList.add("hidden");
      }
    }
    else {
      if((amountOfDisabledPlugins - 4) > 0) {
        button.classList.remove("hidden");
        button.innerHTML = `${baseText} (${amountOfDisabledPlugins - 4})`;
      } else {
        button.classList.add("hidden");
      }
    }
  }

  setButtonAmountText();
  button.addEventListener("click", updateVisibility);
  checkbox.addEventListener("change", setButtonAmountText);
}

document.addEventListener("DOMContentLoaded", (event) => {
  togglePlugins("optional-plugin-container");
})
