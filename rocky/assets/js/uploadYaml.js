import { onDomReady } from "./imports/utils.js";

onDomReady(main);

/*
Depends on component with structure:

details.expandable-code
    summary
    [
    div.content-container[data-yml-code]
        span[data-copy-btn]
        pre
            code
    ]

That also depended by expandable-code.scss for styling
*/

function main() {
  // div.content-container
  const ymlExampleDivs = document.querySelectorAll("div[data-yml-code]");

  const copySpans = document.querySelectorAll("span[data-copy-btn]");
  ymlExampleDivs.forEach((divElm) => {
    divElm.firstElementChild.addEventListener("click", (e) => {
      const example = e.target.nextElementSibling.firstElementChild.textContent;
      navigator.clipboard.writeText(example);
      copySpans.forEach((b) => (b.textContent = "copy"));
      e.target.textContent = "copied!";
    });
  });
}
