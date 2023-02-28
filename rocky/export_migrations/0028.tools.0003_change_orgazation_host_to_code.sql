--
-- Remove field octopoes_host from organization
--
ALTER TABLE "tools_organization" DROP COLUMN "octopoes_host" CASCADE;
--
-- Add field organization to job
--
ALTER TABLE "tools_job" ADD COLUMN "organization_id" bigint NULL CONSTRAINT "tools_job_organization_id_b70002f4_fk_tools_organization_id" REFERENCES "tools_organization"("id") DEFERRABLE INITIALLY DEFERRED; SET CONSTRAINTS "tools_job_organization_id_b70002f4_fk_tools_organization_id" IMMEDIATE;
--
-- Add field code to organization
--
ALTER TABLE "tools_organization" ADD COLUMN "code" varchar(8) NULL UNIQUE;
CREATE INDEX "tools_job_organization_id_b70002f4" ON "tools_job" ("organization_id");
CREATE INDEX "tools_organization_code_2b5bb996_like" ON "tools_organization" ("code" varchar_pattern_ops);