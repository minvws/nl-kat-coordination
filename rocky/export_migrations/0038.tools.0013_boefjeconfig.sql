--
-- Create model BoefjeConfig
--
CREATE TABLE "tools_boefjeconfig" ("id" bigserial NOT NULL PRIMARY KEY, "boefje" varchar(128) NOT NULL, "enabled" boolean NOT NULL, "organization_id" bigint NULL);
ALTER TABLE "tools_boefjeconfig" ADD CONSTRAINT "tools_boefjeconfig_boefje_organization_id_205c41c1_uniq" UNIQUE ("boefje", "organization_id");
ALTER TABLE "tools_boefjeconfig" ADD CONSTRAINT "tools_boefjeconfig_organization_id_ebaa577e_fk_tools_org" FOREIGN KEY ("organization_id") REFERENCES "tools_organization" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "tools_boefjeconfig_organization_id_ebaa577e" ON "tools_boefjeconfig" ("organization_id");
