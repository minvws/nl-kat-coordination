/// <reference types="cypress" />

import strings from "../helpers/stringHelper.js";

context('Findings', () => {
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
    cy.fixture('findingTypes').as('findingTypes');
    cy.fixture('findings').as('findings');
  });


  it('can add a new KAT finding', function() {
    const katId = 'KAT-TEST';

    const { props } = this.findings.Finding;

    cy.get('header').contains('Objects').click();
    cy.get('table tbody tr td:first-child').contains(props.related_ooi).click();

    cy.get('#select_ooi_type').select('Finding');
    cy.get('[type=submit]').contains('Add object').click();

    cy.get('#id_finding_type_ids').type(katId);
    cy.get('#id_proof').type('Het bewijs van testen.');
    cy.get('#id_description').type('De omschrijving van testen.');
    cy.get('#id_reproduce').type('En hoe te reproduceren natuurlijk');

    cy.get('#id_date').type(strings.today);

    cy.get('button[type=submit]').contains('Add Finding').click();

    cy.url().should('include', props.related_ooi);
    cy.get('tbody > tr > td:nth-child(3)').contains(katId);
  });


  it('can add a new CVE finding', function() {
    const findingType = this.findingTypes.CveFindingType.props;
    const related_ooi = "TestNetwork";

    cy.get('header').contains('Objects').click();
    cy.get('table tbody tr td:first-child').contains(related_ooi).click();

    cy.get('#select_ooi_type').select('Finding');
    cy.get('[type=submit]').contains('Add object').click();

    cy.get('#id_finding_type_ids').type(findingType.id);
    cy.get('#id_proof').type('Het bewijs van testen.');
    cy.get('#id_description').type('De omschrijving van testen.');
    cy.get('#id_reproduce').type('En hoe te reproduceren natuurlijk');
    cy.get('#id_date').type(strings.today);

    cy.get('button[type=submit]').contains('Add Finding').click();

    cy.url().should('include', related_ooi);
    cy.get('tbody > tr > td:nth-child(3)').contains(findingType.id);
  });


  it('can add a new finding with multiple finding types.', function() {
    const katIds = 'KAT-ADDED-BY-FINDING,KAT-TEST-305';
    const related_oois = [
        this.objects.Network.props.name,
        this.objects.IPAddressV4.props.address,
        this.objects.IPAddressV6.props.address,
    ];

    for (const related_ooi of related_oois) {
        cy.get('header').contains('Objects').click();
        cy.get('table tbody tr td:first-child').contains(related_ooi).click();

        cy.get('#select_ooi_type').select('Finding');
        cy.get('[type=submit]').contains('Add object').click();

        cy.get('#id_finding_type_ids').type(katIds);
        cy.get('#id_proof').type(`Proof that ${related_ooi} has been tested.`);
        cy.get('#id_description').type(`We must not forget to add some more\n detailed info on how ${related_ooi} has been tested.`);
        cy.get('#id_reproduce').type(`And of course, how do we reproduce this on '${related_ooi}'.`);
        cy.get('#id_date').type(strings.today);

        cy.get('button[type=submit]').contains('Add Finding').click();

        cy.url().should('include', encodeURIComponent(related_ooi));
        strings.split(katIds).forEach(katId => {
          cy.get('tbody > tr > td:nth-child(3)').contains(katId);
        });
    }
  });


  it('can add a finding with findingtypes multiple comma / newline.', function() {
    const related_ooi = "TestNetwork";
    const katIds = 'KAT-TEST,KAT-TEST-305,\n\n\n,KAT-TEST-306,,CVE-2021-35448';

    cy.get('header').contains('Objects').click();
    cy.get('table tbody tr td:first-child').contains(related_ooi).click();

    cy.get('#select_ooi_type').select('Finding');
    cy.get('[type=submit]').contains('Add object').click();

    cy.get('#id_finding_type_ids').type(katIds);
    cy.get('#id_proof').type('Het bewijs van testen.');
    cy.get('#id_description').type('De omschrijving van testen.');
    cy.get('#id_reproduce').type('En hoe te reproduceren natuurlijk');
    cy.get('#id_date').type(strings.today);

    cy.get('button[type=submit]').contains('Add Finding').click();

    cy.url().should('include', related_ooi);

    strings.split(katIds).forEach(katId => {
      cy.get('tbody > tr > td:nth-child(3)').contains(katId);
    });
  });


  it.skip('can add findings in the past.', function() {
    const related_ooi = '9.8.7.6';
    const katIds = 'KAT-TEST,KAT-TEST-305';
    const dates = [strings.yesterday, strings.lastYear, strings.lastWeek];

    for (const date of dates) {
      cy.log(`Adding findings for ${date}`)
      cy.get('header').contains('Objects').click();
      cy.get('table tbody tr td:first-child').contains(related_ooi).click();

      cy.get('#select_ooi_type').select('Finding');
      cy.get('[type=submit]').contains('Add object').click();

      cy.get('#id_finding_type_ids').type(katIds);
      cy.get('#id_proof').type(`Het bewijs van testen.\n\nlogdate: ${date}`);
      cy.get('#id_description').type(`De omschrijving van testen.\n\nlogdate: ${date}`);
      cy.get('#id_reproduce').type(`En hoe te reproduceren natuurlijk.\n\nlogdate: ${date}`);
      cy.get('#id_date').type(date);

      cy.get('button[type=submit]').contains('Add Finding').click();

      cy.url().should('include', related_ooi);

      strings.split(katIds).forEach(katId => {
        cy.get('tbody > tr > td:nth-child(3)').contains(katId);
      });
    }
  });
});
