var nav = document.querySelector('nav.collapsible');
var nav_items = document.querySelectorAll('nav.collapsible > div > .collapsing-element > ul li a');
var screen_width_on_breakpoint = -1;
var nav_items_total_width;
var nav_items_parent_width;

// The gap of all nav_items combined
var nav_items_gap_width = getComputedStyle(nav_items[0].parentElement.parentElement).gap.split("px")[0] * nav_items.length;

var nav_items_parent = nav_items[0].parentElement.parentElement;
// var nav_items_parent = document.querySelector('nav.collapsible .collapsing-element');

function calcWidth(items) {
  var totalWidth = 0;
  for (var i = 0; i < items.length; i++) {
    totalWidth += Math.ceil((items[i].getBoundingClientRect().width));
  }
  return totalWidth;
}

function showHamburger(items_width, parent_width) {
  if (screen_width_on_breakpoint > 0 && window.innerWidth > screen_width_on_breakpoint) {
    nav.classList.remove("collapsed");
    screen_width_on_breakpoint = -1;
  }
  else {
    if(items_width > parent_width) {
      if (screen_width_on_breakpoint < 0) {
        screen_width_on_breakpoint = window.innerWidth;
      }
      nav.classList.add("collapsed");
    } else {
      nav.classList.remove("collapsed");
    }
  }
}

window.addEventListener('resize', function(event) {
  nav_items_parent_width = Math.ceil(nav_items_parent.getBoundingClientRect().width) - 20;
  nav_items_total_width = calcWidth(nav_items) + nav_items_gap_width;

  showHamburger(nav_items_total_width, nav_items_parent_width);
}, true);

document.addEventListener("DOMContentLoaded", function(event) {

  nav_items_parent_width = Math.ceil(nav_items_parent.getBoundingClientRect().width) - 20;
  nav_items_total_width = calcWidth(nav_items) + nav_items_gap_width;

  showHamburger(nav_items_total_width, nav_items_parent_width);
});
