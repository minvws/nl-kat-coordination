--
-- Remove field user from job
--
ALTER TABLE "tools_job" DROP COLUMN "user_id" CASCADE;
--
-- Remove field level from scanprofile
--
ALTER TABLE "tools_scanprofile" DROP COLUMN "level" CASCADE;
--
-- Remove field user from scanprofile
--
ALTER TABLE "tools_scanprofile" DROP COLUMN "user_id" CASCADE;
