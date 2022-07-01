
Cypress.Commands.add('navToOrganizations', function() {
    cy.get('header nav[data-media="(max-width: 56rem)"]').contains('Organizations').click();
});

Cypress.Commands.add('navToOrganizationDetail', function(organizationName) {
    cy.navToOrganizations();
    cy.get('main table tr td:first-child').contains(organizationName).click();
});

Cypress.Commands.add('switchToOrganization', function(organizationName) {
    cy.navToOrganizationDetail(organizationName);
    cy.get('.button.ghost').contains(`Use KAT as ${organizationName}`).click();
});

Cypress.Commands.add('canNotNavToOrganizations', function(organizationName) {
    cy.get('header nav[data-media="(max-width: 56rem)"]')
        .contains('Organizations')
        .should('not.exist');
});

Cypress.Commands.add('canNotNavToOrganizationMembers', function(organizationName) {
    // Nav by Members-link in primary nav bar
    cy.get('header nav').contains('Members').should('not.exist');

    // Nav by organization-detail Members-tab
    cy.get('header nav[data-media="(max-width: 56rem)"]').then(navBar => {
        if (navBar.text().includes('Organizations')) {
            cy.navToOrganizationDetail('Development Organization');
            cy.get('.tabs').contains('Members').should('not.exist');
        }
    });
});

Cypress.Commands.add('submitOrganizationMemberAddForm', function(user) {
    cy.get('#id_group').select(user.group);
    cy.get('#id_name').clear().type(user.name);
    cy.get('#id_email').clear().type(user.email);
    cy.get('#id_password').clear().type(user.pass);
    cy.get('#main-content button[type="submit"]').click();

    cy.contains('Member added succesfully.');
});
