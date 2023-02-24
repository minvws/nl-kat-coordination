--
-- Rename field created_at on job to created
--
ALTER TABLE "tools_job" RENAME COLUMN "created_at" TO "created";
--
-- Rename field tool_module on job to module
--
ALTER TABLE "tools_job" RENAME COLUMN "tool_module" TO "module";