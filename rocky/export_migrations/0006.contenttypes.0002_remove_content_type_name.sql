--
-- Change Meta options on contenttype
--
--
-- Alter field name on contenttype
--
ALTER TABLE "django_content_type" ALTER COLUMN "name" DROP NOT NULL;
--
-- MIGRATION NOW PERFORMS OPERATION THAT CANNOT BE WRITTEN AS SQL:
-- Raw Python operation
--
--
-- Remove field name from contenttype
--
ALTER TABLE "django_content_type" DROP COLUMN "name" CASCADE;
