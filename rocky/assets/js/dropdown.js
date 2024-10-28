const dropdowns = document.querySelectorAll(".dropdown");

dropdowns.forEach((dropdown) => {
  const dropdownButton = dropdown.querySelector(".dropdown-button");

  const toggle = (e) => {
    const activeButton = document.querySelector(
      ".dropdown-button[aria-expanded='true']",
    );
    const isOpen = dropdownButton.getAttribute("aria-expanded") === "true";
    const dropdownList = document.getElementById(
      dropdownButton.getAttribute("aria-controls"),
    );

    if (activeButton && activeButton !== dropdownButton) {
      const activeList = document.getElementById(
        activeButton.getAttribute("aria-controls"),
      );
      activeButton.setAttribute("aria-expanded", "false");
    }

    if (isOpen) {
      dropdownButton.setAttribute("aria-expanded", "false");
    } else {
      dropdownButton.setAttribute("aria-expanded", "true");
    }

    e.stopPropagation();
  };

  dropdownButton.addEventListener("click", toggle);
});

document.addEventListener("click", () => {
  const activeButton = document.querySelector(
    ".dropdown-button[aria-expanded='true']",
  );
  const activeDropdown = activeButton?.closest(".dropdown");

  if (activeDropdown && !activeDropdown.contains(e.target)) {
    const activeList = document.getElementById(
      activeButton.getAttribute("aria-controls"),
    );
    activeButton.setAttribute("aria-expanded", "false");
  }
});
