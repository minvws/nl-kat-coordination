--
-- Alter field octopoes_host on organization
--
ALTER TABLE "tools_organization" ADD CONSTRAINT "tools_organization_octopoes_host_cf356a0b_uniq" UNIQUE ("octopoes_host");
CREATE INDEX "tools_organization_octopoes_host_cf356a0b_like" ON "tools_organization" ("octopoes_host" varchar_pattern_ops);