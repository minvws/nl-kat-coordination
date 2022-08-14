--
-- Create model PasswordHistory
--
CREATE TABLE "password_history_passwordhistory" ("id" serial NOT NULL PRIMARY KEY, "password" varchar(255) NOT NULL, "date" timestamp with time zone NOT NULL);
--
-- Create model UserPasswordHistoryConfig
--
CREATE TABLE "password_history_userpasswordhistoryconfig" ("id" serial NOT NULL PRIMARY KEY, "date" timestamp with time zone NOT NULL, "salt" varchar(120) NOT NULL, "iterations" integer NULL, "user_id" integer NOT NULL);
--
-- Add field user_config to passwordhistory
--
ALTER TABLE "password_history_passwordhistory" ADD COLUMN "user_config_id" integer NOT NULL CONSTRAINT "password_history_pas_user_config_id_20af20ac_fk_password_" REFERENCES "password_history_userpasswordhistoryconfig"("id") DEFERRABLE INITIALLY DEFERRED; SET CONSTRAINTS "password_history_pas_user_config_id_20af20ac_fk_password_" IMMEDIATE;
--
-- Alter unique_together for userpasswordhistoryconfig (1 constraint(s))
--
ALTER TABLE "password_history_userpasswordhistoryconfig" ADD CONSTRAINT "password_history_userpas_user_id_iterations_fa725dcb_uniq" UNIQUE ("user_id", "iterations");
--
-- Alter unique_together for passwordhistory (1 constraint(s))
--
ALTER TABLE "password_history_passwordhistory" ADD CONSTRAINT "password_history_passwor_user_config_id_password_788e1175_uniq" UNIQUE ("user_config_id", "password");
ALTER TABLE "password_history_userpasswordhistoryconfig" ADD CONSTRAINT "password_history_use_user_id_bc5676f2_fk_auth_user" FOREIGN KEY ("user_id") REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "password_history_userpasswordhistoryconfig_user_id_bc5676f2" ON "password_history_userpasswordhistoryconfig" ("user_id");
CREATE INDEX "password_history_passwordhistory_user_config_id_20af20ac" ON "password_history_passwordhistory" ("user_config_id");