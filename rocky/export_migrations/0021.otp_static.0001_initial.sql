--
-- Create model StaticDevice
--
CREATE TABLE "otp_static_staticdevice" ("id" serial NOT NULL PRIMARY KEY, "name" varchar(64) NOT NULL, "confirmed" boolean NOT NULL, "user_id" integer NOT NULL);
--
-- Create model StaticToken
--
CREATE TABLE "otp_static_statictoken" ("id" serial NOT NULL PRIMARY KEY, "token" varchar(16) NOT NULL, "device_id" integer NOT NULL);
ALTER TABLE "otp_static_staticdevice" ADD CONSTRAINT "otp_static_staticdevice_user_id_7f9cff2b_fk_auth_user_id" FOREIGN KEY ("user_id") REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "otp_static_staticdevice_user_id_7f9cff2b" ON "otp_static_staticdevice" ("user_id");
ALTER TABLE "otp_static_statictoken" ADD CONSTRAINT "otp_static_statictok_device_id_74b7c7d1_fk_otp_stati" FOREIGN KEY ("device_id") REFERENCES "otp_static_staticdevice" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "otp_static_statictoken_token_d0a51866" ON "otp_static_statictoken" ("token");
CREATE INDEX "otp_static_statictoken_token_d0a51866_like" ON "otp_static_statictoken" ("token" varchar_pattern_ops);
CREATE INDEX "otp_static_statictoken_device_id_74b7c7d1" ON "otp_static_statictoken" ("device_id");