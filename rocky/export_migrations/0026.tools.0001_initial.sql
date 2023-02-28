--
-- Create model Organization
--
CREATE TABLE "tools_organization" ("id" bigserial NOT NULL PRIMARY KEY, "name" varchar(126) NOT NULL, "octopoes_host" varchar(126) NULL);
--
-- Create model OrganizationMember
--
CREATE TABLE "tools_organizationmember" ("id" bigserial NOT NULL PRIMARY KEY, "authorized" boolean NOT NULL, "status" varchar(64) NOT NULL, "member_name" varchar(126) NOT NULL, "member_role" varchar(126) NOT NULL, "goal" varchar(256) NOT NULL, "organization_id" bigint NULL, "user_id" integer NOT NULL UNIQUE);
--
-- Create model Job
--
CREATE TABLE "tools_job" ("id" uuid NOT NULL PRIMARY KEY, "tool_module" varchar(128) NOT NULL, "arguments" jsonb NOT NULL, "dispatches" jsonb NOT NULL, "created_at" timestamp with time zone NOT NULL, "user_id" integer NULL);
--
-- Create model Indemnification
--
CREATE TABLE "tools_indemnification" ("id" bigserial NOT NULL PRIMARY KEY, "organization_id" bigint NULL, "user_id" integer NULL);
ALTER TABLE "tools_organizationmember" ADD CONSTRAINT "tools_organizationme_organization_id_4d4f92f6_fk_tools_org" FOREIGN KEY ("organization_id") REFERENCES "tools_organization" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "tools_organizationmember" ADD CONSTRAINT "tools_organizationmember_user_id_c135c874_fk_auth_user_id" FOREIGN KEY ("user_id") REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "tools_organizationmember_organization_id_4d4f92f6" ON "tools_organizationmember" ("organization_id");
ALTER TABLE "tools_job" ADD CONSTRAINT "tools_job_user_id_2991a692_fk_auth_user_id" FOREIGN KEY ("user_id") REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "tools_job_user_id_2991a692" ON "tools_job" ("user_id");
ALTER TABLE "tools_indemnification" ADD CONSTRAINT "tools_indemnificatio_organization_id_f53a711e_fk_tools_org" FOREIGN KEY ("organization_id") REFERENCES "tools_organization" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "tools_indemnification" ADD CONSTRAINT "tools_indemnification_user_id_2e9bb970_fk_auth_user_id" FOREIGN KEY ("user_id") REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "tools_indemnification_organization_id_f53a711e" ON "tools_indemnification" ("organization_id");
CREATE INDEX "tools_indemnification_user_id_2e9bb970" ON "tools_indemnification" ("user_id");