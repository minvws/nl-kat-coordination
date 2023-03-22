--
-- Remove field first_name from katuser
--
ALTER TABLE "account_katuser" DROP COLUMN "first_name" CASCADE;
--
-- Remove field last_name from katuser
--
ALTER TABLE "account_katuser" DROP COLUMN "last_name" CASCADE;
