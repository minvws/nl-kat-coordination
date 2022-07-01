/// <reference types="cypress" />

import strings from "../helpers/stringHelper";

context('Register form', () => {
  beforeEach(() => {
    cy.fixture('users').as('users');
    cy.fixture('urls').as('urls');
  });


  describe("create new account", function() {
    it("should be able to visit and submit the form", function() {
      const randomString = strings.random(4);
      const email = this.users.client.new.email.replace("{RANDOM_STRING}", randomString);
      const newUser = {
        ...this.users.client.new,
        email
      };

      cy.goTo("register");

      cy.get('#id_organization_name').type(`${newUser.organization} ${randomString}`);
      cy.get('#id_member_name').type(newUser.name);
      cy.get('#id_member_role').type(newUser.role);
      cy.get('#id_authorized').check();
      cy.get('#id_goal').type(newUser.goal);
      cy.get('#id_email').type(newUser.email);
      cy.get('#id_password').type(newUser.pass);

      cy.get('#main-content button[type="submit"]').click();

      cy.get('.page-meta').should('not.contain', 'Logged in as');
    });
  });
});
