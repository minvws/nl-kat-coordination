--
-- Alter field last_login on user
--
ALTER TABLE "auth_user" ALTER COLUMN "last_login" DROP NOT NULL;
