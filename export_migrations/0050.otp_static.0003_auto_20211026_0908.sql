--
-- Alter field id on staticdevice
--
SET CONSTRAINTS "otp_static_statictoken_device_id_74b7c7d1_fk" IMMEDIATE; ALTER TABLE "otp_static_statictoken" DROP CONSTRAINT "otp_static_statictoken_device_id_74b7c7d1_fk";
ALTER TABLE "otp_static_staticdevice" ALTER COLUMN "id" TYPE bigint USING "id"::bigint;
DROP SEQUENCE IF EXISTS "otp_static_staticdevice_id_seq" CASCADE;
CREATE SEQUENCE "otp_static_staticdevice_id_seq";
ALTER TABLE "otp_static_staticdevice" ALTER COLUMN "id" SET DEFAULT nextval('"otp_static_staticdevice_id_seq"');
SELECT setval('"otp_static_staticdevice_id_seq"', MAX("id")) FROM "otp_static_staticdevice";
ALTER SEQUENCE "otp_static_staticdevice_id_seq" OWNED BY "otp_static_staticdevice"."id";
ALTER TABLE "otp_static_statictoken" ALTER COLUMN "device_id" TYPE bigint USING "device_id"::bigint;
ALTER TABLE "otp_static_statictoken" ADD CONSTRAINT "otp_static_statictoken_device_id_74b7c7d1_fk" FOREIGN KEY ("device_id") REFERENCES "otp_static_staticdevice" ("id") DEFERRABLE INITIALLY DEFERRED;
--
-- Alter field id on statictoken
--
ALTER TABLE "otp_static_statictoken" ALTER COLUMN "id" TYPE bigint USING "id"::bigint;
DROP SEQUENCE IF EXISTS "otp_static_statictoken_id_seq" CASCADE;
CREATE SEQUENCE "otp_static_statictoken_id_seq";
ALTER TABLE "otp_static_statictoken" ALTER COLUMN "id" SET DEFAULT nextval('"otp_static_statictoken_id_seq"');
SELECT setval('"otp_static_statictoken_id_seq"', MAX("id")) FROM "otp_static_statictoken";
ALTER SEQUENCE "otp_static_statictoken_id_seq" OWNED BY "otp_static_statictoken"."id";