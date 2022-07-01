/// <reference types="cypress" />

context('Objects delete', () => {
  Cypress.Cookies.defaults({
    preserve: ['sessionid', 'csrftoken'],
  });

  before(() => {
    cy.login({
      user: Cypress.env('superuser_user'),
      pass: Cypress.env('superuser_pass')
    });
  });

  beforeEach(() => {
    cy.fixture('users').as('users');
    cy.fixture('objects').as('objects');
  });


  it('can remove a Network', function() {
    const ooi = {
      ...this.objects.Network.props,
      name: "Remove This TestNetwork",
    };
    const ooi_id = `Network|${ooi.name}`

    // add OOI to remove
    cy.navTo('ooiAdd', { ooiType: ooi.ooi_type });
    cy.get('#id_name').type(ooi.name);
    cy.get('button[type=submit]').contains(`Add ${ooi.ooi_type}`).click();
    cy.get('h1').contains(ooi.name);
    cy.urlIsOoiDetail(ooi_id);

    // remove OOI
    cy.get('.button-container').contains('Delete').click();

    cy.url().should('include', '/delete/');
    cy.contains('Are you sure');

    cy.get('.button-container').contains(`Delete ${ooi.ooi_type}`).click();

    cy.url().should('include', '/objects/');
    cy.url().should('not.include', '/delete/');

    // reloading, object can still exist because of slow XTDB
    cy.wait(2000);
    cy.reload(true);

    cy.get('table').should('not.contain', ooi.name);
  });
});
