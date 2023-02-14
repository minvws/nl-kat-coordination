--
-- Add field signal_group_id to organization
--
ALTER TABLE "tools_organization" ADD COLUMN "signal_group_id" varchar(126) NULL;
--
-- Add field signal_username to organization
--
ALTER TABLE "tools_organization" ADD COLUMN "signal_username" varchar(126) NULL UNIQUE;
--
-- Add field signal_username to organizationmember
--
ALTER TABLE "tools_organizationmember" ADD COLUMN "signal_username" varchar(126) NULL UNIQUE;
CREATE INDEX "tools_organization_signal_username_6d4078c4_like" ON "tools_organization" ("signal_username" varchar_pattern_ops);
CREATE INDEX "tools_organizationmember_signal_username_7abd8fef_like" ON "tools_organizationmember" ("signal_username" varchar_pattern_ops);