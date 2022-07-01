/// <reference types='cypress' />

const totp = require('totp-generator');
import strings from '../helpers/stringHelper';
import user from '../helpers/userHelper';

context('Organization', () => {
  Cypress.Cookies.defaults({
    preserve: ['sessionid', 'csrftoken'],
  });

  beforeEach(() => {
    cy.fixture('users').as('users');
    cy.fixture('urls').as('urls');
  });

  describe('superuser', function() {
      const randomString = strings.random(4);

      before(() => {
        cy.login({
          user: Cypress.env('superuser_user'),
          pass: Cypress.env('superuser_pass')
        });
      });

      it('should be able to add organization', function() {
        cy.log('permission "add_organization"');
        const admin = user.newUser({
          user: this.users.admin.new,
          randomString
        });

        cy.navToOrganizations();
        cy.get('.button').contains('Add new organization').click();

        cy.get('#id_name').clear().type(admin.organization);
        cy.get('#id_code').clear().type(`_${randomString}`);
        cy.get('#main-content button[type="submit"]').click();

        cy.contains('Organization added succesfully.');
      });

      it('should be able to add organization member', function() {
        cy.log('permission "add_organizationmember"');
        const admin = user.newUser({
          user: this.users.admin.new,
          randomString
        });

        cy.navToOrganizations();
        cy.contains(admin.organization).click();

        cy.get('.tabs').contains('Members').click();
        cy.get('.button').contains('Add new member').click();

        cy.submitOrganizationMemberAddForm(admin);
      });

      it('should be able to switch organization', function () {
        const admin = user.newUser({
          user: this.users.admin.new,
          randomString
        });

        cy.switchToOrganization(admin.organization);
      });
  });

  describe('admin', function() {
      before(() => {
        cy.login({
          user: Cypress.env('admin_user'),
          pass: Cypress.env('admin_pass')
        });
      });

      it('should not be able to switch organization', function () {
        cy.log('permission "can_switch_organization"');
        cy.canNotNavToOrganizations();
      });

      it('should not be able to add organization', function() {
        cy.log('permission "add_organization"');
        cy.canNotNavToOrganizations();
      });

      it('should be able to add organization member', function() {
        cy.log('permission "add_organizationmember"');
        const admin = user.newUser({
          user: this.users.admin.new
        });

        cy.get('header nav').contains('Members').click();
        cy.get('.button').contains('Add new member').click();

        cy.submitOrganizationMemberAddForm(admin);
      });
  });


  describe('redteam', function() {
      before(() => {
        cy.login({
          user: Cypress.env('redteam_user'),
          pass: Cypress.env('redteam_pass')
        });
      });

      it('should be able to switch organization', function () {
        cy.log('permission "can_switch_organization"');

        cy.switchToOrganization('Development Organization');
      });

      it('should not be able to add organization', function() {
        cy.log('permission "add_organization"');

        cy.navToOrganizations();
        cy.get('.button').contains('Add new organization').should('not.exist');
      });

      it('should not be able to view members of organization', function() {
        cy.log('permission "view_organizationmember"');
        cy.canNotNavToOrganizationMembers();
      });
  });

  describe('client', function() {
      before(() => {
        cy.login({
          user: Cypress.env('client_user'),
          pass: Cypress.env('client_pass')
        });
      });

      it('should not be able to navigate to Organization List', function () {
        cy.log('permission "can_switch_organization"');
        cy.canNotNavToOrganizations();
      });

      it('should not be able to view members of organization', function() {
        cy.log('permission "view_organizationmember"');
        cy.canNotNavToOrganizationMembers();
      });
  });
});
