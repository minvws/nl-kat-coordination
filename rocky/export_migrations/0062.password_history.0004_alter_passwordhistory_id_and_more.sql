BEGIN;
--
-- Alter field id on passwordhistory
--
ALTER TABLE "password_history_passwordhistory" ALTER COLUMN "id" TYPE bigint USING "id"::bigint;
DROP SEQUENCE IF EXISTS "password_history_passwordhistory_id_seq" CASCADE;
CREATE SEQUENCE "password_history_passwordhistory_id_seq";
ALTER TABLE "password_history_passwordhistory" ALTER COLUMN "id" SET DEFAULT nextval('"password_history_passwordhistory_id_seq"');
SELECT setval('"password_history_passwordhistory_id_seq"', MAX("id")) FROM "password_history_passwordhistory";
ALTER SEQUENCE "password_history_passwordhistory_id_seq" OWNED BY "password_history_passwordhistory"."id";
--
-- Alter field id on userpasswordhistoryconfig
--
SET CONSTRAINTS "password_history_pas_user_config_id_20af20ac_fk_password_" IMMEDIATE; ALTER TABLE "password_history_passwordhistory" DROP CONSTRAINT "password_history_pas_user_config_id_20af20ac_fk_password_";
ALTER TABLE "password_history_userpasswordhistoryconfig" ALTER COLUMN "id" TYPE bigint USING "id"::bigint;
DROP SEQUENCE IF EXISTS "password_history_userpasswordhistoryconfig_id_seq" CASCADE;
CREATE SEQUENCE "password_history_userpasswordhistoryconfig_id_seq";
ALTER TABLE "password_history_userpasswordhistoryconfig" ALTER COLUMN "id" SET DEFAULT nextval('"password_history_userpasswordhistoryconfig_id_seq"');
SELECT setval('"password_history_userpasswordhistoryconfig_id_seq"', MAX("id")) FROM "password_history_userpasswordhistoryconfig";
ALTER SEQUENCE "password_history_userpasswordhistoryconfig_id_seq" OWNED BY "password_history_userpasswordhistoryconfig"."id";
ALTER TABLE "password_history_passwordhistory" ALTER COLUMN "user_config_id" TYPE bigint USING "user_config_id"::bigint;
ALTER TABLE "password_history_passwordhistory" ADD CONSTRAINT "password_history_passwordhistory_user_config_id_20af20ac_fk" FOREIGN KEY ("user_config_id") REFERENCES "password_history_userpasswordhistoryconfig" ("id") DEFERRABLE INITIALLY DEFERRED;
COMMIT;
