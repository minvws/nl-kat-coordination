// @ts-check

import {
    closest,
    ensureElementHasId,
    onDomReady,
    prependNode,
  } from "./imports/utils.js";

  onDomReady(initSidemenus);

  /**
   * Add a close/open toggle behaviour to the sidemenus. Safe to call again to
   * apply to newly added sidemenus.
   */
  export function initSidemenus() {
    var sidemenus = document.querySelectorAll(".sidemenu > nav");
    for (var i = 0; i < sidemenus.length; i++) {
      var sidemenu = sidemenus[i];
      if (!(sidemenu instanceof HTMLElement)) {
        continue;
      }
      if (!sidemenu.querySelector("button.sidemenu-toggle")) {
        addToggleButton(sidemenu);
        defineScrollPosition(sidemenu);
      }
    }
  }

  /**
   * @param {HTMLElement} sidemenu
   */

  function addToggleButton(sidemenu) {
    var main = closest(sidemenu, ".sidemenu");
    var ol = sidemenu.querySelector("ol");

    if (!main || !ol) {
      return;
    }

    ensureElementHasId(ol);

    var openLabel = sidemenu.dataset.openLabel || "Zijbalknavigatie";
    var closeLabel = sidemenu.dataset.closeLabel || "Sluit zijbalknavigatie";
    var toggleButtonType = sidemenu.dataset.toggleButtonType || "ghost";

    var button = document.createElement("button");
    button.type = "button";
    button.classList.add(toggleButtonType, "sidemenu-toggle");
    button.setAttribute("aria-controls", ol.id);

    function isClosed() {
      return main.classList.contains("sidemenu-closed");
    }

    function setClosed(closed) {
      button.innerText = closed ? closeLabel : openLabel;
      button.setAttribute("aria-expanded", String(!closed));
      if (closed) {
        main.classList.add("sidemenu-closed");
      } else {
        main.classList.remove("sidemenu-closed");
      }
    }

    setClosed(isClosed());

    button.addEventListener("click", function () {
      setClosed(!isClosed());
    });

    prependNode(sidemenu, button);
  }


  /**
   * @param {HTMLElement} sidemenu
   */

  function defineScrollPosition(sidemenu) {
    const pageHeaderElement = document.getElementById('page-header');
    const pageFooterElement = document.getElementById('page-footer');
    const stickyElement = document.getElementById("sticky-overflow");
    let stickyElementOGMaxHeight = getComputedStyle(stickyElement).getPropertyValue("max-height");
    let pageHeaderHeight = pageHeaderElement?.offsetHeight;
    let pageFooterHeight = pageFooterElement?.offsetHeight;

    window.addEventListener("resize", (event => {
      // Set the height of the page header and footer
      // when the size of the window changes,
      // to account for responsive behaviour
      pageHeaderHeight = pageHeaderElement?.offsetHeight;
      pageFooterHeight = pageFooterElement?.offsetHeight;
    }));

    window.addEventListener("scroll", (event => {
      // Amount of PX the page is scrolled
      let scrollCount = document.scrollingElement?.scrollTop;

      console.log(stickyElementOGMaxHeight)

      if(scrollCount > pageHeaderHeight) {
        stickyElement.style.maxHeight = "calc(100vh - " + (pageHeaderHeight + pageFooterHeight) + ")";
        stickyElement.style.maxHeight = "calc(100vh - 232px)";
      } else {
        stickyElement.style.maxHeight = stickyElementOGMaxHeight;
      }

      // console.log(scrollCount)
    }));
  }
