--
-- Alter field name on organization
--
ALTER TABLE "tools_organization" ADD CONSTRAINT "tools_organization_name_4209b368_uniq" UNIQUE ("name");
CREATE INDEX "tools_organization_name_4209b368_like" ON "tools_organization" ("name" varchar_pattern_ops);