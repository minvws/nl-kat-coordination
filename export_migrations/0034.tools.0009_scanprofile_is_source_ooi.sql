--
-- Add field is_source_ooi to scanprofile
--
ALTER TABLE "tools_scanprofile" ADD COLUMN "is_source_ooi" boolean DEFAULT false NOT NULL;
ALTER TABLE "tools_scanprofile" ALTER COLUMN "is_source_ooi" DROP DEFAULT;