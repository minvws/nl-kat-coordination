const dropdowns = document.querySelectorAll(".dropdown");
let activeDropdown = null; // To track the currently active dropdown

const closeActiveDropdown = () => {
  if (activeDropdown) {
    const activeButton = activeDropdown.querySelector(".dropdown-button");
    const activeList = activeDropdown.querySelector(".dropdown-list");

    activeButton.setAttribute("aria-expanded", "false");
    activeList.classList.remove("open");

    activeDropdown = null;
  }
};

dropdowns.forEach((dropdown) => {
  const dropdownButton = dropdown.querySelector(".dropdown-button");
  const dropdownList = dropdown.querySelector(".dropdown-list");

  const toggle = (e) => {
    const isOpen = dropdownButton.getAttribute("aria-expanded") === "true";

    closeActiveDropdown();

    if (!isOpen) {
      dropdownButton.setAttribute("aria-expanded", "true");
      dropdownList.classList.add("open");
      activeDropdown = dropdown;
    } else {
      dropdownButton.setAttribute("aria-expanded", "false");
      dropdownList.classList.remove("open");
      activeDropdown = null;
    }

    e.stopPropagation();
  };

  dropdownButton.addEventListener("click", toggle);
});

document.addEventListener("click", (e) => {
  if (activeDropdown && !activeDropdown.contains(e.target)) {
    closeActiveDropdown();
  }
});
