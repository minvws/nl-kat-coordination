--
-- Change Meta options on organization
--
--
-- Remove field is_source_ooi from scanprofile
--
ALTER TABLE "tools_scanprofile" DROP COLUMN "is_source_ooi" CASCADE;
--
-- Add field onboarded to organizationmember
--
ALTER TABLE "tools_organizationmember" ADD COLUMN "onboarded" boolean DEFAULT false NOT NULL;
ALTER TABLE "tools_organizationmember" ALTER COLUMN "onboarded" DROP DEFAULT;
