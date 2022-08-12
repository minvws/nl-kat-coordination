// ***********************************************
// This example commands.js shows you how to
// create various custom commands and overwrite
// existing commands.
//
// For more comprehensive examples of custom
// commands please read more here:
// https://on.cypress.io/custom-commands
// ***********************************************
//
//
// -- This is a parent command --
// Cypress.Commands.add('login', (email, password) => { ... })
//
//
// -- This is a child command --
// Cypress.Commands.add('drag', { prevSubject: 'element'}, (subject, options) => { ... })
//
//
// -- This is a dual command --
// Cypress.Commands.add('dismiss', { prevSubject: 'optional'}, (subject, options) => { ... })
//
//
// -- This will overwrite an existing command --
// Cypress.Commands.overwrite('visit', (originalFn, url, options) => { ... })

const totp = require("totp-generator");

const cleanPath = (path) => {
  return path.length && path[0] === "/" ? path.slice(1) : path;
};

const getUrl = (url, path) => {
  return url + cleanPath(path);
};

Cypress.Commands.add("goTo", function (page) {
  if (this.urls.path[page]) {
    cy.visit(getUrl(Cypress.env("base_url"), this.urls.path[page]));
  } else if (page.charAt() === "/") {
    cy.visit(getUrl(Cypress.env("base_url"), page));
  } else if (page.substr(0, 4) === "http") {
    cy.visit(page);
  }
});

Cypress.Commands.add("login", function ({ user, pass }, navToLogin = true) {
  if (navToLogin) {
    cy.setCookie("language", "en");
    cy.visit(getUrl(Cypress.env("base_url"), "/account/login/"));
  }

  cy.enterLoginCredentials({ user, pass });
  cy.enterOTP();

  cy.get("body").then(($body) => {
    if ($body.text().includes("Invalid token")) {
      cy.log("Invalid token; wait 30s for token refresh");
      cy.wait(30000);
      cy.enterOTP();
    }
  });

  cy.getCookie("sessionid").should("exist").as("sessionid");
});

Cypress.Commands.add("enterLoginCredentials", function ({ user, pass }) {
  cy.get("#id_auth-username").type(user);
  cy.get("#id_auth-password").type(pass);
  cy.get('button[type="submit"]').contains("Next").click();
});

Cypress.Commands.add("enterOTP", function () {
  const otp_secret = Cypress.env("client_otp_secret");
  const token = totp(otp_secret);

  cy.get("#id_token-otp_token").clear().type(token);
  cy.get('button[type="submit"]').contains("Next").click();
});

Cypress.Commands.add("urlIsOoiDetail", function (ooiId) {
  const query = new URLSearchParams(`?ooi_id=${ooiId}`);
  cy.url().should("include", query.toString());
});

Cypress.Commands.add("isOoiDetailPage", function ({ id, title, ooiType }) {
  cy.refreshOn404();
  cy.urlIsOoiDetail(id);
  cy.get("h1").contains(title);
  cy.get("table thead")
    .contains("Declarations")
    .parents("table")
    .contains(ooiType);
});

Cypress.Commands.add("switchOnBoefje", function (boefjeName) {
  cy.navTo("katalogus");
  cy.get(".plugins h1")
    .contains(boefjeName)
    .parents('div[role="group"]')
    .find('button[type="submit"]')
    .then(($button) => {
      if ($button.text() === "Enable") {
        $button.click();
      }
    });
});

Cypress.Commands.add("navTo", function (page, pageArgs = {}) {
  if (page === "ooiAdd") {
    cy.navToHome();
    cy.navToOoiAdd(pageArgs);
  } else if (page === "ooiDetail") {
    cy.navToHome();
    cy.navToOoiDetail(pageArgs);
  } else if (page === "katalogus") {
    cy.navToHome();
    cy.navToKatalogus();
  }
});

Cypress.Commands.add("navToHome", function () {
  cy.get(
    'header nav[data-media="(min-width: 56rem)"] > ul > li:first-child'
  ).click();
});

Cypress.Commands.add("navToKatalogus", function () {
  cy.get("header").contains("KAT-alogus").click();
});

Cypress.Commands.add("navToOoiAdd", function (pageArgs = {}) {
  const { ooiType } = pageArgs;

  cy.get("header").contains("Objects").click();
  cy.get('button[aria-controls="export-add"]').click();
  cy.get("#export-add li").contains("Add object").click();
  cy.get("#select_ooi_type").select(ooiType);
  cy.get("[type=submit]").contains("Add object").click();
});

Cypress.Commands.add("navToOoiDetail", function (pageArgs = {}) {
  const { name } = pageArgs;
  cy.get("header").contains("Objects").click();
  cy.get("tr:first-child").contains(name).click();
});

Cypress.Commands.add("refreshOn404", function () {
  cy.get("body").then(($body) => {
    if ($body.text().includes("Page not found")) {
      cy.log("404: possibly slow environment. Refreshing once in 3s.");
      cy.wait(3000);
    }
  });
});
