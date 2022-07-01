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

	/**
	 * Ponyfill for Element.prototype.closest.
	 * @param {Element} element
	 * @param {DOMString} selectors
	 * @return {Element | null}
	 */
	function closest(element, selectors) {
		if (Element.prototype.closest) {
			return element.closest(selectors);
		}
		var matches =
			Element.prototype.matches ||
			Element.prototype.msMatchesSelector ||
			Element.prototype.webkitMatchesSelector;

		do {
			if (matches.call(element, selectors)) {
				return element;
			}
			element = element.parentElement || element.parentNode;
		} while (element !== null && element.nodeType === 1);

		return null;
	}

	// @ts-check

	var managedTables = new WeakMap();

	onDomReady(initExpandoRows);
	onDomUpdate(initExpandoRows);

	/**
	 * Add a close/open toggle behaviour to expando-rows. Safe to call again to
	 * apply to newly added expando-rows.
	 */
	function initExpandoRows() {
		var tables = document.querySelectorAll("table");
		for (var i = 0; i < tables.length; i++) {
			var table = tables[i];
			if (!(table instanceof HTMLElement)) {
				continue;
			}
			if (
				!(table instanceof HTMLElement) ||
				!table.querySelector(".expando-button") ||
				managedTables.has(table)
			) {
				continue;
			}
			initTable(table);
			managedTables.set(table, true);
		}
		document.body.classList.add("js-expando-rows-loaded");
	}

	/**
	 * Start managing the table's expando-buttons, their corresponding
	 * expando-rows, and the zebra striping of the other rows.
	 * @param {HTMLElement} table
	 */
	function initTable(table) {
		initExpandoButtons(table);
		updateZebra(table);
		onDomUpdate(function () {
			initExpandoButtons(table);
			updateZebra(table);
		}, table);
	}

	/**
	 * Setup the table's expando-buttons to handle clicks and control their
	 * corresponding expando-rows. Safe to call again to apply to newly added
	 * expando-buttons.
	 * @param {HTMLElement} table
	 */
	function initExpandoButtons(table) {
		var buttons = table.querySelectorAll(".expando-button");
		for (var i = 0; i < buttons.length; i++) {
			var button = buttons[i];
			if (
				!(button instanceof HTMLElement) ||
				button.hasAttribute("aria-controls") ||
				button.hasAttribute("disabled")
			) {
				continue;
			}
			initExpandoButton(button);
		}
	}

	/**
	 * Setup an expando-buttons to handle clicks and control its corresponding
	 * expando-row.
	 * @param {HTMLElement} button
	 */
	function initExpandoButton(button) {
		var iconOpenClasses = (
			button.dataset.iconOpenClass || "icon icon-chevron-light-bottom"
		).split(/\s+/);
		var iconCloseClasses = (
			button.dataset.iconCloseClass || "icon icon-chevron-light-top"
		).split(/\s+/);

		var buttonRow = closest(button, "tr");
		var row = buttonRow.nextElementSibling;
		if (
			!(row instanceof HTMLElement) ||
			!(row.tagName === "TR") ||
			!row.classList.contains("expando-row")
		) {
			console.warn(
				"Could not find .expando-row corresponding to .expando-button:",
				button
			);
			button.setAttribute("disabled", "");
			button.classList.add("action-button");
			button.classList.add.apply(
				button.classList,
				expanded ? iconCloseClasses : iconOpenClasses
			);
			return;
		}

		var expanded = button.getAttribute("aria-expanded") === "true";
		var closeLabel, openLabel;
		if (expanded) {
			closeLabel = button.innerText;
			openLabel = button.dataset.openLabel || "Open details";
			button.setAttribute("aria-expanded", "true");
		} else {
			closeLabel = button.dataset.closeLabel || "Sluit details";
			openLabel = button.innerText;
			button.setAttribute("aria-expanded", "false");
			row.setAttribute("hidden", "");
		}

		ensureElementHasId(row);
		button.setAttribute("aria-controls", row.id);
		button.classList.add("action-button");
		button.classList.add.apply(
			button.classList,
			expanded ? iconCloseClasses : iconOpenClasses
		);

		button.addEventListener("click", function () {
			var expand = button.getAttribute("aria-expanded") === "false";
			button.setAttribute("aria-expanded", expand ? "true" : "false");
			if (expand) {
				button.innerHTML = closeLabel;
				button.classList.remove.apply(
					button.classList,
					expanded ? iconOpenClasses : iconCloseClasses
				);
				button.classList.add.apply(
					button.classList,
					expanded ? iconCloseClasses : iconOpenClasses
				);
				row.removeAttribute("hidden");
			} else {
				button.innerHTML = openLabel;
				button.classList.remove.apply(
					button.classList,
					expanded ? iconCloseClasses : iconOpenClasses
				);
				button.classList.add.apply(
					button.classList,
					expanded ? iconOpenClasses : iconCloseClasses
				);
				row.setAttribute("hidden", "");
			}
		});
	}

	/**
	 * Update the rows' .odd/.even override classes.
	 * @param {HTMLElement} table
	 */
	function updateZebra(table) {
		var rows = table.querySelectorAll("tr:not(.expando-row)");
		for (var i = 0; i < rows.length; i++) {
			var row = rows[i];
			if (i % 2) {
				row.classList.add("odd");
				row.classList.remove("even");
			} else {
				row.classList.add("even");
				row.classList.remove("odd");
			}
		}
	}

	exports.initExpandoRows = initExpandoRows;

	Object.defineProperty(exports, '__esModule', { value: true });

	return exports;

}({}));
