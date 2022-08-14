/// <reference types='cypress' />

const totp = require("totp-generator");

context("Login", () => {
  beforeEach(() => {
    cy.fixture("urls").as("urls");
  });

  it("should redirect to querystring NEXT", function () {
    const { baseUrl, path } = this.urls;
    const user = Cypress.env("superuser_user");
    const pass = Cypress.env("superuser_pass");

    cy.visit(baseUrl + path.ooiList);
    cy.url().should("include", `${path.login}?next=${path.ooiList}`);

    cy.enterLoginCredentials({ user, pass });
    cy.enterOTP();

    cy.url().should("not.include", path.login);
    cy.url().should("include", path.ooiList);
  });

  it.skip("should redirect to home when querystring NEXT is not safe", function () {
    const { baseUrl, path } = this.urls;
    const user = Cypress.env("superuser_user");
    const pass = Cypress.env("superuser_user");

    cy.visit(`${baseUrl}${path.login}?next=https:\/\/google.com`);

    cy.enterLoginCredentials({
      user: Cypress.env("superuser_user"),
      pass: Cypress.env("superuser_user"),
    });
    cy.enterOTP();

    cy.url().should("not.include", path.login);
    cy.url().should("include", baseUrl);
  });
});
