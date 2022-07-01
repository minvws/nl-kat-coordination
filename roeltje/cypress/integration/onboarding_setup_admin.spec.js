/// <reference types="cypress" />

import strings from '../helpers/stringHelper';
import getUser from '../helpers/userHelper';

context('Onboarding', () => {
  Cypress.Cookies.defaults({
    preserve: ['sessionid', 'csrftoken'],
  });

  beforeEach(() => {
    cy.fixture('users').as('users');
    cy.fixture('urls').as('urls');
  });


  describe('admin setup', function() {
    const randomString = strings.random(4);

    it('superuser should be able to complete admin setup', function() {
      const admin = getUser({
        user: this.users.admin.new,
        randomString
      });
      const red_team = getUser({
        user: this.users.red_team.new,
        randomString
      });
      const client = getUser({
        user: this.users.client.new,
        randomString
      });

      cy.goTo('onboarding_organization_setup');
      cy.login({
        user: Cypress.env('superuser_user'),
        pass: Cypress.env('superuser_pass')
      }, false);

      // intro page
      cy.get('a.button').contains('Let\'s get started').click();

      // create organization
      cy.get('#id_name').clear().type(admin.organization);
      cy.get('#id_code').clear().type(`_${randomString}`);
      cy.get('#main-content button[type="submit"]').click();

      // go to account setup
      cy.contains('Organization succesfully created');
      cy.get('#main-content a.button').contains('add accounts').click();

      // admin account setup
      cy.get('#id_name').clear().type(admin.name);
      cy.get('#id_email').clear().type(admin.email);
      cy.get('#id_password').clear().type(admin.pass);
      cy.get('#main-content button[type="submit"]').click();

      cy.contains('User succesfully created');

      // redteam account setup
      cy.get('#id_name').clear().type(red_team.name);
      cy.get('#id_email').clear().type(red_team.email);
      cy.get('#id_password').clear().type(red_team.pass);
      cy.get('#main-content button[type="submit"]').click();

      cy.contains('User succesfully created');

      // client account setup
      cy.get('#id_name').clear().type(admin.name);
      cy.get('#id_email').clear().type(client.email);
      cy.get('#id_password').clear().type(client.pass);
      cy.get('#main-content button[type="submit"]').click();

      cy.contains('User succesfully created');

//      cy.contains(admin.organization).click();
    });

    it('should be able to login with new admin credentials', function() {
      const user = getUser({
        user: this.users.admin.new,
        randomString
      });

      cy.goTo('login')
      cy.enterLoginCredentials({
        user: user.email,
        pass: user.pass,
      });

      cy.contains('You are logged in.');
    });

    it('should be able to login with new red-team credentials', function() {
      const user = getUser({
        user: this.users.red_team.new,
        randomString
      });

      cy.goTo('login')
      cy.enterLoginCredentials({
        user: user.email,
        pass: user.pass,
      });

      cy.contains('You are logged in.');
    });

    it('should be able to login with new client credentials', function() {
      const user = getUser({
        user: this.users.admin.new,
        randomString
      });

      cy.goTo('login')
      cy.enterLoginCredentials({
        user: user.email,
        pass: user.pass,
      });

      cy.contains('You are logged in.');
    });

    it('should see error when creating same organization', function() {
      const user = getUser({
        user: this.users.admin.new,
        randomString
      });

      cy.goTo('onboarding_organization_setup');
      cy.login({
        user: Cypress.env('superuser_user'),
        pass: Cypress.env('superuser_pass')
      }, false);

      // intro page
      cy.get('a.button').contains('Let\'s get started').click();

      // create organization
      cy.get('#id_name').clear().type(user.organization);
      cy.get('#id_code').clear().type(`_${randomString}`);
      cy.get('#main-content button[type="submit"]').click();

      cy.contains('Choose another organization.');
      cy.contains('Organization with this Code already exists.');

    });
  });
});
