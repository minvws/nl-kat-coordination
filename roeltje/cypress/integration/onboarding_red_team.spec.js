/// <reference types="cypress" />

import strings from "../helpers/stringHelper";

context('Onboarding', () => {
  Cypress.Cookies.defaults({
    preserve: ['sessionid', 'csrftoken'],
  });

  beforeEach(() => {
    cy.fixture('users').as('users');
    cy.fixture('urls').as('urls');
    cy.fixture('objects').as('objects');
  });


  describe("red team", function() {
    it("should be able to see onboarding steps", function() {
      cy.goTo('onboarding_redteam');
      cy.login({
        user: Cypress.env('redteam_user'),
        pass: Cypress.env('redteam_pass')
      }, false);
      cy.get('[aria-label="current-step"]').contains('1: Introduction');
      cy.get('a.button').contains('Let\'s get started').click();

      cy.get('[aria-label="current-step"]').contains('2: Choose a report');
      cy.get('a.button').contains('Let\'s choose a report').click();

      cy.get('[aria-label="current-step"]').contains('2: Choose a report');
      cy.get('a.button').contains('DNS report').click();

      cy.get('[aria-label="current-step"]').contains('3: Setup scan');
      cy.get('a.button').contains('Add URL').click();

      cy.get('[aria-label="current-step"]').contains('3: Setup scan');
      cy.get('#id_raw').type('https://mispo.es/');
      cy.get('[type=submit]').contains('Create object').click();

      cy.get('[aria-label="current-step"]').contains('3: Setup scan');
      cy.get('#id_level').select('L2');
      cy.get('[type=submit]').contains('Set clearance level').click();

      cy.get('[aria-label="current-step"]').contains('3: Setup scan');
      cy.get('[type=submit]').contains('Enable and start scan').click();

      cy.get('[aria-label="current-step"]').contains('3: Setup scan');
      cy.get('[type=submit]').contains('Got it, generate my report').click();

      // button is disabled for 10 seconds
      cy.wait(11000);
      cy.get('[type=submit]').contains('Open my DNS-report').click();

      cy.url().should('include', this.urls.path['onboarding_dns_report']);
    });
  });
});
