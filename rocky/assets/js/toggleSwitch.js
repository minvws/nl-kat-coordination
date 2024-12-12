import { onDomReady } from "../js/imports/utils.js";

onDomReady(initToggleSwitches);

function initToggleSwitches() {
  // Switches get stitches ;-)
  // Grab all toggle switches
  let toggle_switches = document.querySelectorAll(".toggle-switch");

  for (let i = 0; i < toggle_switches.length; i++) {
    initButtonsAndContentBlocks(toggle_switches[i]);
  }
}

function initButtonsAndContentBlocks(toggle_switch) {
  // Get all the toggle switch options
  let options = toggle_switch.querySelectorAll(".toggle-switch-button");

  for (let i = 0; i < options.length; i++) {
    let option = options[i];

    // Hide all elements linked to toggle switch options.
    document
      .getElementById(option.getAttribute("data-target-id"))
      .classList.add("hidden");

    // Add click listener to switch options.
    option.addEventListener("click", (event) => {
      toggle(event.target, options);
    });

    // Show option that on init has "aria-current".
    if (option.parentElement.hasAttribute("aria-current", "true")) {
      document
      .getElementById(option.getAttribute("data-target-id"))
      .classList.remove("hidden");
    }
  }
}

function toggle(target, options) {
  let target_li = target.closest("li");

  // Check if target isn't already the active one.
  if (!target_li.hasAttribute("aria-current", "true")) {
    for (let i = 0; i < options.length; i++) {
      // Toggle all options to "non active" state.
      options[i].closest("li").removeAttribute("aria-current", "false");
      document
        .getElementById(options[i].getAttribute("data-target-id"))
        .classList.add("hidden");
    }
    // Toggle selected option (target) to active state.
    target_li.setAttribute("aria-current", "true");
    document
      .getElementById(target.getAttribute("data-target-id"))
      .classList.remove("hidden");
  }
}
