(function () {
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

	var initiatedAccordions = new WeakMap();

	onDomReady(initAccordions);
	onDomUpdate(initAccordions);

	function initAccordions() {
		var accordions = document.querySelectorAll(".accordion");
		for (var i = 0; i < accordions.length; i++) {
			var accordion = accordions[i];
			if (initiatedAccordions.has(accordion)) {
				continue;
			}
			if (!(accordion instanceof HTMLElement)) {
				continue;
			}
			initAccordion(accordion);
			initiatedAccordions.set(accordion, true);
		}
		document.body.classList.add("js-accordion-loaded");
	}

	/**
	 * @param {HTMLElement} accordion
	 */
	function initAccordion(accordion) {
		var hasAriaExpandedMarkup = false;
		var buttons = getButtons(accordion);

		for (var i = 0; i < buttons.length; i++) {
			var button = buttons[i];

			// Make sure the button `aria-control`s its sibling <div> by id.
			if (!button.getAttribute("aria-controls")) {
				var sibling = button.nextElementSibling;
				if (!(sibling instanceof HTMLElement) || sibling.tagName !== "DIV") {
					console.error("No sibling <div> found for accordion button:", button);
					continue;
				}
				ensureElementHasId(sibling);
				button.setAttribute("aria-controls", sibling.id);
			}

			// Set up the initial `aria-expanded` state.
			if (button.getAttribute("aria-expanded")) {
				hasAriaExpandedMarkup = true;
			} else {
				button.setAttribute("aria-expanded", "false");
			}

			button.addEventListener("click", function (event) {
				var target = event.target;
				if (!(target instanceof HTMLElement)) {
					return;
				}
				var expanded = target.getAttribute("aria-expanded") === "true";
				target.setAttribute("aria-expanded", expanded ? "false" : "true");
			});
		}

		// Expand the first item by default
		if (!hasAriaExpandedMarkup) {
			buttons[0].setAttribute("aria-expanded", "true");
		}
	}

	/**
	 * @param {HTMLElement} accordion
	 */
	function getButtons(accordion) {
		var buttons = [];
		for (var i = 0; i < accordion.children.length; i++) {
			var container = accordion.children[i];
			for (var j = 0; j < container.children.length; j++) {
				var child = container.children[j];
				if (child.tagName === "BUTTON") {
					buttons.push(child);
				}
			}
		}
		return buttons;
	}

}());
