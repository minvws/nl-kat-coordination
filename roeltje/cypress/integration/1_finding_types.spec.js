/// <reference types="cypress" />

const randomString = (length) => Math.random().toString(36).replace(/[^a-z]+/g, '').substr(0, length);

context('Finding Types', () => {
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
    cy.fixture('findingTypes').as('findingTypes');
    cy.fixture('urls').as('urls');
  })


  it('can add a new finding type', function() {
    const findingTypes = [
      this.findingTypes.KatFindingType1,
      this.findingTypes.KatFindingType2
    ];

    findingTypes.forEach((findingType) => {
      const ooi = findingType.props;

      cy.get('header').contains('KAT').click();
      cy.get('header').contains('Findings').click();
      cy.get('.button').contains('Add finding type').click();

      cy.get('#id_id').type(ooi.id + Cypress._.random(99999));
      cy.get('#id_title').type(ooi.title);
      cy.get('#id_description').type(ooi.description);
      cy.get('#id_risk').select(ooi.risk);
      cy.get('#id_solution').type(ooi.solution);
      cy.get('#id_references').type(ooi.references);
      cy.get('#id_impact_description').type(ooi.impact_description);

      cy.get('button[type=submit]').contains('Add finding type').click();

      cy.urlIsOoiDetail(`KATFindingType|${ooi.id}`);

      cy.contains(ooi.title);
      cy.contains(ooi.description);
      cy.contains(ooi.solution);
      cy.contains(ooi.references);
    });
  });


  it('can add a new finding type without references', function() {
    const ooi = {
      ...this.findingTypes.KatFindingType1.props,
      id: 'KAT-NO-REFERENCES' + Cypress._.random(99999),
    }

    cy.get('header').contains('KAT').click();
    cy.get('header').contains('Findings').click();
    cy.get('.button').contains('Add finding type').click();

    cy.get('#id_id').type(ooi.id);
    cy.get('#id_title').type(ooi.title);
    cy.get('#id_description').type(ooi.description);
    cy.get('#id_risk').select(ooi.risk);
    cy.get('#id_solution').type(ooi.solution);
    cy.get('#id_impact_description').type(ooi.impact_description);

    cy.get('button[type=submit]').contains('Add finding type').click();

    cy.urlIsOoiDetail(`KATFindingType|${ooi.id}`);

    cy.get('body').should('not.contain', 'KatFindingType/extraInfo');
  });
});
