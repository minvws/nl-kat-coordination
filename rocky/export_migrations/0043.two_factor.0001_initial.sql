--
-- Create model PhoneDevice
--
CREATE TABLE "two_factor_phonedevice" ("id" serial NOT NULL PRIMARY KEY, "name" varchar(64) NOT NULL, "confirmed" boolean NOT NULL, "number" varchar(16) NOT NULL, "key" varchar(40) NOT NULL, "method" varchar(4) NOT NULL, "user_id" integer NOT NULL);
ALTER TABLE "two_factor_phonedevice" ADD CONSTRAINT "two_factor_phonedevice_user_id_54718003_fk_auth_user_id" FOREIGN KEY ("user_id") REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "two_factor_phonedevice_user_id_54718003" ON "two_factor_phonedevice" ("user_id");