--
-- Add field verified to organizationmember
--
ALTER TABLE "tools_organizationmember" ADD COLUMN "verified" boolean DEFAULT false NOT NULL;
ALTER TABLE "tools_organizationmember" ALTER COLUMN "verified" DROP DEFAULT;