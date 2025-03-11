--
-- Add field clearance_level to katuser
--
ALTER TABLE "account_katuser" ADD COLUMN "clearance_level" integer DEFAULT  -1 NOT NULL;
ALTER TABLE "account_katuser" ALTER COLUMN "clearance_level" DROP DEFAULT;