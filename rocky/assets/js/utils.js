const htmlElement = document.getElementsByTagName('html')[0];
const language = htmlElement.getAttribute('lang');
const organization_code = htmlElement.getAttribute('data-organization-code');

export {
  language,
  organization_code,
}
