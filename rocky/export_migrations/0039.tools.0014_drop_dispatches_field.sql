--
-- Remove field dispatches from job
--
ALTER TABLE "tools_job" DROP COLUMN "dispatches" CASCADE;
--
-- Rename field boefje_name on job to boefje_id
--
ALTER TABLE "tools_job" RENAME COLUMN "boefje_name" TO "boefje_id";