var nav = document.querySelector('nav.collapsible');
var nav_items = document.querySelectorAll('nav.collapsible > div > .collapsing-element > ul li a');
var nav_items_width_on_breakpoint = 0;

// The gap of all nav_items combined
var nav_items_gap_width = getComputedStyle(nav_items[0].parentElement.parentElement).gap.split("px")[0] * nav_items.length;

var nav_items_parent = nav_items[0].parentElement.parentElement;
// var nav_items_parent = document.querySelector('nav.collapsible .collapsing-element');
var nav_items_parent_width = Math.ceil(nav_items_parent.getBoundingClientRect().width);

function calcWidth(items) {
  var totalWidth = 0;
  for (var i = 0; i < items.length; i++) {
    totalWidth += Math.ceil((items[i].getBoundingClientRect().width));
  }
  return totalWidth;
}

function showHamburger(items_width, parent_width) {
  // console.log(items_width)
  // console.log(nav_items_width_on_breakpoint)
  if(items_width > parent_width) {
    nav_items_width_on_breakpoint = calcWidth(nav_items) + nav_items_gap_width;
    console.log(nav_items_width_on_breakpoint)
    console.log(parent_width)
    // console.log('collapsed')
    nav.classList.add("collapsed");
  } else {
    // console.log('not collapsed')
    nav.classList.remove("collapsed");
  }
}

window.addEventListener('resize', function(event) {
  nav_items_total_width = calcWidth(nav_items) + nav_items_gap_width;
  showHamburger(nav_items_total_width, nav_items_parent_width);
}, true);

document.addEventListener("DOMContentLoaded", function(event) {
  nav_items_total_width = calcWidth(nav_items) + nav_items_gap_width;
  showHamburger(nav_items_total_width, nav_items_parent_width);
});
