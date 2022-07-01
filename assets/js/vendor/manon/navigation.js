(function (exports) {
	'use strict';

	/**
	 * Run the given callback function once after the DOM is ready.
	 *
	 * @param {() => void} fn
	 */
	function onDomReady(fn) {
		if (document.readyState !== "loading") return fn();
		document.addEventListener("DOMContentLoaded", fn);
	}

	/**
	 * Provide the given element with a unique generated `id`, if it does not have one already.
	 *
	 * @param {HTMLElement} element
	 */
	function ensureElementHasId(element) {
		if (!element.id) {
			element.id =
				element.tagName + "-" + (~~(Math.random() * 1e9) + 1e9).toString(16);
		}
	}

	/**
	 * Set up a matchMedia change event listener. Returns a function that, when
	 * called, will remove the event listener again.
	 *
	 * @param {string} media
	 * @param {(event: { matches: boolean }) => void} handler
	 * @return {() => void}
	 */
	function onMediaQueryMatch(media, handler) {
		var mql = window.matchMedia(media);

		if (mql.addEventListener) {
			mql.addEventListener("change", handler);
		} else {
			mql.addListener(handler);
		}

		handler(mql);

		return function remove() {
			if (mql.addEventListener) {
				mql.removeEventListener("change", handler);
			} else {
				mql.removeListener(handler);
			}
		};
	}

	// @ts-check

	onDomReady(initNaviation);

	/**
	 * Add responsive behaviour to header navigation. Safe to call again to make a
	 * newly added header navigation responsive.
	 */
	function initNaviation() {
		var headers = document.querySelectorAll("header:not(.breadcrumbs)");
		for (var i = 0; i < headers.length; i++) {
			var nav = headers[i].querySelector("nav");
			if (!(nav instanceof HTMLElement) || nav.querySelector(".menu_toggle")) {
				continue;
			}
			var isCondensed = headers[i].className.indexOf("condensed") !== -1;
			makeResponsive(nav, isCondensed);
		}
	}

	/**
	 * @param {HTMLElement} nav
	 * @param {boolean} isCondensed
	 */
	function makeResponsive(nav, isCondensed) {
		var menu = nav.querySelector("ul, ol");
		if (!(menu instanceof HTMLElement)) {
			return;
		}
		ensureElementHasId(menu);

		var button = createMenuButton(
			menu,
			nav.dataset.openLabel || "Menu",
			nav.dataset.closeLabel || "Sluit menu"
		);

		menu.parentNode.insertBefore(button.element, menu);

		if (!isCondensed) {
			onMediaQueryMatch(
				nav.dataset.media || "(min-width: 42rem)",
				function (event) {
					button.setExpanded(false);
					if (event.matches) {
						nav.classList.remove("collapsible-menu");
					} else {
						nav.classList.add("collapsible-menu");
					}
				}
			);
		}
	}

	/**
	 * @param {HTMLElement} ul
	 * @param {string} openLabel
	 * @param {string} closeLabel
	 * @return {{ element: HTMLButtonElement, setExpanded: (expanded: boolean) => void }}
	 */
	function createMenuButton(ul, openLabel, closeLabel) {
		var button = document.createElement("button");
		button.className = "menu_toggle";
		button.setAttribute("hidden", "false");
		button.setAttribute("aria-controls", ul.id);
		button.setAttribute("aria-expanded", "false");

		var label = document.createElement("span");
		label.innerText = openLabel;
		label.className = "sr-only";
		ensureElementHasId(label);

		button.appendChild(label);
		button.setAttribute("aria-labelledby", label.id);

		function setExpanded(expanded) {
			if (expanded !== (button.getAttribute("aria-expanded") === "true")) {
				button.setAttribute("aria-expanded", String(expanded));
				label.innerText = expanded ? closeLabel : openLabel;
			}
		}

		button.addEventListener("click", function () {
			setExpanded(button.getAttribute("aria-expanded") === "false");
		});

		return {
			element: button,
			setExpanded: setExpanded,
		};
	}

	exports.initNaviation = initNaviation;

	Object.defineProperty(exports, '__esModule', { value: true });

	return exports;

}({}));
