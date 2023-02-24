--
-- Create model TOTPDevice
--
CREATE TABLE "otp_totp_totpdevice" ("id" serial NOT NULL PRIMARY KEY, "name" varchar(64) NOT NULL, "confirmed" boolean NOT NULL, "key" varchar(80) NOT NULL, "step" smallint NOT NULL CHECK ("step" >= 0), "t0" bigint NOT NULL, "digits" smallint NOT NULL CHECK ("digits" >= 0), "tolerance" smallint NOT NULL CHECK ("tolerance" >= 0), "drift" smallint NOT NULL, "last_t" bigint NOT NULL, "user_id" integer NOT NULL);
ALTER TABLE "otp_totp_totpdevice" ADD CONSTRAINT "otp_totp_totpdevice_user_id_0fb18292_fk_auth_user_id" FOREIGN KEY ("user_id") REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "otp_totp_totpdevice_user_id_0fb18292" ON "otp_totp_totpdevice" ("user_id");