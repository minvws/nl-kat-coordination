function togglePlugins(containerClass) {
  const container = document.querySelector(`.${containerClass}`);
  const checkbox = container.querySelector('.show-all-toggle');
  const hiddenPlugins = container.querySelectorAll('.plugin.hidden');

  function updateVisibility() {
    hiddenPlugins.forEach(function (plugin) {
      if(checkbox.checked) {
        plugin.classList.remove('hidden')
      } else {
        plugin.classList.add('hidden')
      }
    });
  }

  updateVisibility();
  checkbox.addEventListener('change', updateVisibility)
}

document.addEventListener('DOMContentLoaded', (event) => {
  togglePlugins('optional-plugin-container');
})
