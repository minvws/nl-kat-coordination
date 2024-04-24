function toggleEnabledPlugins(containerClass) {
  const container = document.querySelector(`.${containerClass}`);
  const checkbox = document.querySelector(`.${containerClass}` + ' .display-toggle');
  console.log("Checkbox: ", checkbox);
  const enabledPlugins = container.querySelectorAll('.plugin-enabled');

  function updateVisibility() {
    enabledPlugins.forEach(function (plugin) {
      plugin.style.display = checkbox.checked ? 'flex' : 'none';
    });
  }

  updateVisibility();
  checkbox.addEventListener('change', updateVisibility)
}

document.addEventListener('DOMContentLoaded', (event) => {
  toggleEnabledPlugins('required-plugin-container');
  toggleEnabledPlugins('optional-plugin-container');
})
