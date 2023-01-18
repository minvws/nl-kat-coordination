--
-- Add field acknowledged_clearance_level to organizationmember
--
ALTER TABLE "tools_organizationmember" ADD COLUMN "acknowledged_clearance_level" integer DEFAULT 0 NOT NULL;
ALTER TABLE "tools_organizationmember" ALTER COLUMN "acknowledged_clearance_level" DROP DEFAULT;
--
-- Add field trusted_clearance_level to organizationmember
--
ALTER TABLE "tools_organizationmember" ADD COLUMN "trusted_clearance_level" integer DEFAULT 0 NOT NULL;
ALTER TABLE "tools_organizationmember" ALTER COLUMN "trusted_clearance_level" DROP DEFAULT;