function initAutoSubmitters() {
  let autoSubmitters = document.getElementsByClassName("submit-on-click");
  Array.from(autoSubmitters).forEach(addSubmitOnClick)
}

function addSubmitOnClick(item) {
  item.onclick = function() {
    item.closest("form").submit();
  }
}

document.addEventListener('DOMContentLoaded', (event) => {
  initAutoSubmitters();
})