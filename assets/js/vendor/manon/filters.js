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
	 * Set up a MutationObserver. Returns a disconnect function.
	 * @param {() => void} handler
	 * @param {HTMLElement | undefined} [root]
	 * @return {undefined|() => void}
	 */
	function onDomUpdate(handler, root) {
		if ("MutationObserver" in window) {
			var observer = new MutationObserver(handler);
			observer.observe(root || document, { childList: true, subtree: true });
			return observer.disconnect.bind(observer);
		}
	}

	// @ts-check

	var initiatedFilterToggles = new WeakMap();

	onDomReady(initFilterToggles);
	onDomUpdate(initFilterToggles);

	/**
	 * Add a close/open toggle behaviour to the filters. Safe to call again to
	 * apply to newly added filters.
	 */
	function initFilterToggles() {
		var filterToggles = document.querySelectorAll(".filter > div > button");
		for (var i = 0; i < filterToggles.length; i++) {
			var filterToggle = filterToggles[i];
			if (
				initiatedFilterToggles.has(filterToggle) ||
				!(filterToggle instanceof HTMLElement)
			) {
				continue;
			}
			initFilterToggle(filterToggle);
			initiatedFilterToggles.set(filterToggle, true);
		}
		document.body.classList.add("js-filters-loaded");
	}

	/**
	 * @param {HTMLElement} filterToggle
	 */
	function initFilterToggle(filterToggle) {
		var filter = filterToggle.parentNode.parentNode;
		if (!(filter instanceof HTMLElement)) {
			return;
		}
		var form = filter.querySelector("form");
		if (!(form instanceof HTMLElement)) {
			console.error(
				"Could not find <form> corresponding to filter toggle:",
				filterToggle
			);
			return;
		}
		var expanded = filterToggle.getAttribute("aria-expanded") !== "false";
		var hideLabel, showLabel;
		if (expanded) {
			hideLabel = filterToggle.innerText;
			showLabel = filterToggle.dataset.showFiltersLabel || "Toon filters";
		} else {
			hideLabel = filterToggle.dataset.hideFiltersLabel || "Verberg filters";
			showLabel = filterToggle.innerText;
		}
		ensureElementHasId(filter);
		filterToggle.setAttribute("aria-controls", filter.id);
		if (expanded) {
			filterToggle.setAttribute("aria-expanded", "true");
		} else {
			form.setAttribute("hidden", "");
		}
		filterToggle.addEventListener("click", function () {
			var expand = filterToggle.getAttribute("aria-expanded") == "false";
			filterToggle.setAttribute("aria-expanded", expand ? "true" : "false");
			filterToggle.innerHTML = expand ? hideLabel : showLabel;
			if (expand) {
				form.removeAttribute("hidden");
			} else {
				form.setAttribute("hidden", "");
			}
		});
	}

	exports.initFilterToggles = initFilterToggles;

	Object.defineProperty(exports, '__esModule', { value: true });

	return exports;

}({}));
