--
-- Alter field reference on scanprofile
--
ALTER TABLE "tools_scanprofile" ALTER COLUMN "reference" TYPE text USING "reference"::text;