const dropdowns = document.querySelectorAll(".dropdown");

dropdowns.forEach((dropdown) => {
  const dropdownButton = dropdown.querySelector(".dropdown-button");
  const dropdownList = dropdown.querySelector(".dropdown-list");

  const toggle = () => {
    if (dropdownList.getAttribute("aria-expanded") == "true") {
      closeDropdown();
    } else {
      dropdownList.setAttribute("aria-expanded", "true");
      document.addEventListener("click", handleClose);
    }
  };

  const handleClose = (event) => {
    if (event.target == dropdownButton) {
      return;
    }

    closeDropdown();
  };

  const closeDropdown = () => {
    document.removeEventListener("click", handleClose);
    dropdownList.setAttribute("aria-expanded", "false");
  };

  dropdownButton.addEventListener("click", () => toggle());
});
