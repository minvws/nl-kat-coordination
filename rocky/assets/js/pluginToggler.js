function togglePlugins(containerClass) {
  const container = document.querySelector(`.${containerClass}`);
  const button = container.querySelector('#more-suggested-plugins');
  const checkbox = document.getElementById("checkbox-for-enabled-optional-plugins");


  // Toggle "overflow" when amount of plugins exceed 4 (We only show 1 row containing 4 items, initially)
  function updateVisibility() {
    container.classList.toggle("hide-overflow");
    setButtonAmountText();
  }

  function setButtonAmountText() {
    const elementsHtmlCollection = container.getElementsByClassName('plugin');
    const itemsArray = Array.prototype.slice.call(elementsHtmlCollection);

    let disabledCounter = 0;

    // Determine amount of not yet enabled plugins
    itemsArray.forEach((pluginElement) => {
      if(pluginElement.classList.contains('plugin-is-disabled')) {
        disabledCounter++;
      }
    });

    let baseText = ""

    // Determine if the button text should be "Show" or "Hide"
    if(container.classList.contains('hide-overflow')) {
      baseText = button.dataset.showText
    } else {
      baseText = button.dataset.hideText
    }


    // Determine amount of "to be shown" plugins. Hide button if amount !> 0
    if(checkbox.checked) {
      if((itemsArray.length - 4 > 0)) {
        button.classList.remove("hidden")
        button.innerHTML = `${baseText} (${itemsArray.length - 4})`
      } else {
        button.classList.add("hidden")
      }
    }
    else {
      if((disabledCounter - 4) > 0) {
        button.classList.remove("hidden")
        button.innerHTML = `${baseText} (${disabledCounter - 4})`
      } else {
        button.classList.add("hidden")
      }
    }
  }

  setButtonAmountText();
  button.addEventListener('click', updateVisibility)
  checkbox.addEventListener('change', setButtonAmountText)
}

document.addEventListener('DOMContentLoaded', (event) => {
  togglePlugins('optional-plugin-container');
})
