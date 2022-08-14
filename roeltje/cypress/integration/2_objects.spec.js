/// <reference types="cypress" />

context("Objects", () => {
  Cypress.Cookies.defaults({
    preserve: ["sessionid", "csrftoken"],
  });

  before(() => {
    cy.login({
      user: Cypress.env("superuser_user"),
      pass: Cypress.env("superuser_pass"),
    });
  });

  beforeEach(() => {
    cy.fixture("users").as("users");
    cy.fixture("objects").as("objects");
  });

  it("can add a new Network", function () {
    const { ooi_id, props: ooi } = this.objects.Network;

    cy.navTo("ooiAdd", { ooiType: ooi.ooi_type });
    cy.get("#id_name").type(ooi.name);
    cy.get("[type=submit]").contains(`Add ${ooi.ooi_type}`).click();

    cy.isOoiDetailPage({ id: ooi_id, title: ooi.name, ooiType: ooi.ooi_type });
  });

  it("can add a new IP Address v4", function () {
    const { ooi_id, props: ooi } = this.objects.IPAddressV4;
    const network = this.objects.Network;

    cy.navTo("ooiAdd", { ooiType: ooi.ooi_type });
    cy.get("#id_address").type(ooi.address);
    cy.get("#id_network").select(`${network.ooi_id}`);
    cy.get("button[type=submit]").contains(`Add ${ooi.ooi_type}`).click();

    cy.isOoiDetailPage({
      id: ooi_id,
      title: ooi.address,
      ooiType: ooi.ooi_type,
    });
  });

  it("can add a new IP Address v6", function () {
    const { ooi_id, props: ooi } = this.objects.IPAddressV6;
    const network = this.objects.Network;

    cy.navTo("ooiAdd", { ooiType: ooi.ooi_type });

    cy.get("#id_network").select(network.ooi_id);

    cy.get("#id_address").type(ooi.address);

    cy.get("button[type=submit]").contains(`Add ${ooi.ooi_type}`).click();

    cy.get("h1").contains(ooi.address);
    cy.urlIsOoiDetail(ooi_id);
    cy.get("table thead")
      .contains("Declarations")
      .parents("table")
      .contains("IPAddressV6");
  });

  it("can not add a new IP Port without an IP Address", function () {
    const ooi = this.objects.IPPort.props;
    const network = this.objects.Network.props;
    const ipAddress = this.objects.IPAddressV4;

    cy.navTo("ooiAdd", { ooiType: ooi.ooi_type });
    cy.get("#id_protocol").type(ooi.protocol);
    cy.get("#id_port").type(ooi.port);
    cy.get("#id_state").type(ooi.state);
    cy.get("button[type=submit]").contains(`Add ${ooi.ooi_type}`).click();

    cy.url().should("include", `/add/${ooi.ooi_type}/`);
  });

  it("can add a new IP Port on an IP Address", function () {
    const { ooi_id, props: ooi } = this.objects.IPPort;
    const network = this.objects.Network.props;
    const ipAddress = this.objects.IPAddressV4;

    cy.navTo("ooiAdd", { ooiType: ooi.ooi_type });

    cy.get("#id_address").select(ipAddress.ooi_id);
    cy.get("#id_protocol").select(ooi.protocol);
    cy.get("#id_port").type(ooi.port);
    cy.get("#id_state").type(ooi.state);
    cy.get("button[type=submit]").contains(`Add ${ooi.ooi_type}`).click();

    cy.isOoiDetailPage({ id: ooi_id, title: ooi.port, ooiType: ooi.ooi_type });
  });

  it("can add a new Hostname", function () {
    const { ooi_id, props: ooi } = this.objects.Hostname;

    cy.navTo("ooiAdd", { ooiType: ooi.ooi_type });
    cy.get("#id_network").select(ooi.Network);
    cy.get("#id_name").type(ooi.name);
    cy.get("button[type=submit]").contains(`Add ${ooi.ooi_type}`).click();

    cy.isOoiDetailPage({ id: ooi_id, title: ooi.title, ooiType: ooi.ooi_type });
  });

  it("can add a new DNSZone", function () {
    const { ooi_id, props: ooi } = this.objects.DNSZone;
    const hostname = this.objects.Hostname;

    cy.navTo("ooiAdd", { ooiType: ooi.ooi_type });
    cy.get("#id_hostname").select(hostname.ooi_id);
    cy.get("button[type=submit]").contains(`Add ${ooi.ooi_type}`).click();

    cy.isOoiDetailPage({ id: ooi_id, title: ooi.title, ooiType: ooi.ooi_type });
  });

  it("can add a new Service", function () {
    const { ooi_id, props: ooi } = this.objects.Service;

    cy.navTo("ooiAdd", { ooiType: ooi.ooi_type });
    cy.get("#id_name").type(ooi.name);
    cy.get("button[type=submit]").contains(`Add ${ooi.ooi_type}`).click();

    cy.isOoiDetailPage({ id: ooi_id, title: ooi.title, ooiType: ooi.ooi_type });
  });

  it("can add a new IPService", function () {
    const { ooi_id, props: ooi } = this.objects.IPService;

    cy.navTo("ooiAdd", { ooiType: ooi.ooi_type });

    cy.get("#id_ip_port").select(ooi.IPPort);
    cy.get("#id_service").select(ooi.Service);
    cy.get("button[type=submit]").contains(`Add ${ooi.ooi_type}`).click();

    cy.isOoiDetailPage({ id: ooi_id, title: ooi.title, ooiType: ooi.ooi_type });
  });

  it("can add a new Website", function () {
    const { ooi_id, props: ooi } = this.objects.Website;

    cy.navTo("ooiAdd", { ooiType: ooi.ooi_type });
    cy.get("#id_ip_service").select(ooi.IPService);
    cy.get("#id_hostname").select(ooi.Hostname);
    cy.get("button[type=submit]").contains(`Add ${ooi.ooi_type}`).click();

    cy.isOoiDetailPage({ id: ooi_id, title: ooi.title, ooiType: ooi.ooi_type });
  });

  it("can add a new object with a trailing slash", function () {
    const { ooi_id, props } = this.objects.Network;
    const ooi = {
      ...props,
      name: "This/TestNetwork/Has/Slashes/",
    };

    cy.navTo("ooiAdd", { ooiType: ooi.ooi_type });
    cy.get("#id_name").type(ooi.name);
    cy.get("button[type=submit]").contains(`Add ${ooi.ooi_type}`).click();

    cy.isOoiDetailPage({ id: ooi_id, title: ooi.name, ooiType: ooi.ooi_type });
  });

  it("can add a URL", function () {
    const { ooi_id, props: ooi } = this.objects.URL;

    cy.navTo("ooiAdd", { ooiType: ooi.ooi_type });
    cy.get("#id_network").select(`${ooi.Network}`);
    cy.get("#id_raw").type(ooi.url);
    cy.get("button[type=submit]").contains(`Add ${ooi.ooi_type}`).click();

    cy.isOoiDetailPage({ id: ooi_id, title: ooi.title, ooiType: ooi.ooi_type });
  });
});
