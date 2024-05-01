function togglePlugins(containerClass) {
  const container = document.querySelector(`.${containerClass}`);
  const button = container.querySelector('#more-suggested-plugins');

  function updateVisibility() {
    container.classList.toggle("hide-overflow")
  }

  updateVisibility();
  button.addEventListener('click', updateVisibility)
}

document.addEventListener('DOMContentLoaded', (event) => {
  togglePlugins('optional-plugin-container');
})
