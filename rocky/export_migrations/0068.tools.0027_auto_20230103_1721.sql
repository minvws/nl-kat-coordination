--
-- Remove field signal_group_id from organization
--
ALTER TABLE "tools_organization" DROP COLUMN "signal_group_id" CASCADE;
--
-- Remove field signal_username from organization
--
ALTER TABLE "tools_organization" DROP COLUMN "signal_username" CASCADE;
--
-- Alter field code on organization
--
ALTER TABLE "tools_organization" ALTER COLUMN "code" TYPE varchar(32), ALTER COLUMN "code" SET NOT NULL;
--
-- Alter field name on organization
--
--
-- Create model OrganizationTag
--
CREATE TABLE "tools_organizationtag" ("id" bigserial NOT NULL PRIMARY KEY, "name" varchar(255) NOT NULL UNIQUE, "slug" varchar(50) NOT NULL, "count" integer NOT NULL, "protected" boolean NOT NULL, "path" text NOT NULL, "label" varchar(255) NOT NULL, "level" integer NOT NULL, "color" varchar(20) NOT NULL, "border_type" varchar(20) NOT NULL, "parent_id" bigint NULL);
--
-- Add field tags to organization
--
CREATE TABLE "tools_organization_tags" ("id" bigserial NOT NULL PRIMARY KEY, "organization_id" bigint NOT NULL, "organizationtag_id" bigint NOT NULL);
ALTER TABLE "tools_organizationtag" ADD CONSTRAINT "tools_organizationtag_slug_parent_id_b448e963_uniq" UNIQUE ("slug", "parent_id");
ALTER TABLE "tools_organizationtag" ADD CONSTRAINT "tools_organizationta_parent_id_44222957_fk_tools_org" FOREIGN KEY ("parent_id") REFERENCES "tools_organizationtag" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "tools_organizationtag_name_7a671965_like" ON "tools_organizationtag" ("name" varchar_pattern_ops);
CREATE INDEX "tools_organizationtag_slug_0110d5be" ON "tools_organizationtag" ("slug");
CREATE INDEX "tools_organizationtag_slug_0110d5be_like" ON "tools_organizationtag" ("slug" varchar_pattern_ops);
CREATE INDEX "tools_organizationtag_parent_id_44222957" ON "tools_organizationtag" ("parent_id");
ALTER TABLE "tools_organization_tags" ADD CONSTRAINT "tools_organization_tags_organization_id_organiza_55e193db_uniq" UNIQUE ("organization_id", "organizationtag_id");
ALTER TABLE "tools_organization_tags" ADD CONSTRAINT "tools_organization_t_organization_id_75b3a1ee_fk_tools_org" FOREIGN KEY ("organization_id") REFERENCES "tools_organization" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "tools_organization_tags" ADD CONSTRAINT "tools_organization_t_organizationtag_id_760070bd_fk_tools_org" FOREIGN KEY ("organizationtag_id") REFERENCES "tools_organizationtag" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "tools_organization_tags_organization_id_75b3a1ee" ON "tools_organization_tags" ("organization_id");
CREATE INDEX "tools_organization_tags_organizationtag_id_760070bd" ON "tools_organization_tags" ("organizationtag_id");