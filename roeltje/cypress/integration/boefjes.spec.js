/// <reference types="cypress" />

context('Boefjes', () => {
  Cypress.Cookies.defaults({
    preserve: ['sessionid', 'csrftoken'],
  });

  beforeEach(() => {
    cy.fixture('urls').as('urls');
    cy.fixture('users').as('users');
  });

  const firstToggleBtn = 'main .plugins [role="group"]:first-child button[type="submit"]';

  describe('client', function() {
      before(() => {
        cy.login({
          user: Cypress.env('client_user'),
          pass: Cypress.env('client_pass'),
        });
      });

      it('should not be able toggle boefjes', () => {
        cy.navToKatalogus();
        cy.get(firstToggleBtn).should('be.disabled');
      });
  });

  describe('redteamer', function() {
      before(() => {
        cy.login({
          user: Cypress.env('redteam_user'),
          pass: Cypress.env('redteam_pass'),
        });
      });

      it('should be able toggle boefjes', () => {
        cy.navToKatalogus();
        cy.get(firstToggleBtn).should('be.enabled');
      });
  });

  describe('admin', function() {
      before(() => {
        cy.login({
          user: Cypress.env('admin_user'),
          pass: Cypress.env('admin_pass'),
        });
      });

      it('should not be able toggle boefjes', () => {
        cy.navToKatalogus();
        cy.get(firstToggleBtn).should('be.disabled');
      });
  });

  describe('superuser', function() {
      before(() => {
        cy.login({
          user: Cypress.env('superuser_user'),
          pass: Cypress.env('superuser_pass')
        });
      });

      it('can toggle first boefje in card grid', function() {
        let toggleFromEnabled = true;

        cy.get('header').contains('KAT-alogus').click();

        cy.get(firstToggleBtn).then(($button) => {
          if ($button.text() === 'Disable') {
            toggleFromEnabled = false;
          }
          cy.log(`Toggle from ${toggleFromEnabled ? 'enabled' : 'disabled'}`);
        });

        cy.get(firstToggleBtn).click();
        cy.get(firstToggleBtn).then(($button) => {
          if (toggleFromEnabled) {
            expect($button.text()).to.eq('Disable');
          } else {
            expect($button.text()).to.eq('Enable');
          }
        });

        cy.get(firstToggleBtn).click();
        cy.get(firstToggleBtn).then(($button) => {
          if (toggleFromEnabled) {
            expect($button.text()).to.eq('Enable');
          } else {
            expect($button.text()).to.eq('Disable');
          }
        });
      });

      it('can start DNS boefjes on hostname', function() {
        cy.switchOnBoefje('Dnssec');
        cy.switchOnBoefje('DnsRecords');

        cy.navTo('ooiAdd', {ooiType: 'Network'});
        cy.get('#id_name').type('internet');
        cy.get('button[type=submit]').contains('Add Network').click();

        cy.wait(1000); // octopoes can be slow at times

        cy.navTo('ooiAdd', { ooiType: 'Hostname'});
        cy.get('#id_network').select('Network|internet');
        cy.get('#id_name').type('mispo.es');
        cy.get('button[type=submit]').contains('Add Hostname').click();

        cy.get('table tr').contains('Dnssec').parents('tr').contains('Start Scan').click();

        cy.contains('Your scan is running successfully in the background.');

        const lastRunTask = 'table tbody tr:first-child';
        cy.get(lastRunTask).contains('dns-sec');
        cy.get(lastRunTask).contains('STARTED');

        // assuming DNSSec is done in 3.5s
        cy.wait(3500);
        cy.reload();

        cy.get(lastRunTask).contains('SUCCESS');

        cy.navTo('ooiDetail', {name: 'mispo.es'});
        cy.get('table thead').contains("Findings").parents('table').contains('KAT-600 @ mispo.es');
      });
  });
});
