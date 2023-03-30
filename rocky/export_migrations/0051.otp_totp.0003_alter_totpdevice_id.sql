--
-- Alter field id on totpdevice
--
ALTER TABLE "otp_totp_totpdevice" ALTER COLUMN "id" TYPE bigint USING "id"::bigint;
DROP SEQUENCE IF EXISTS "otp_totp_totpdevice_id_seq" CASCADE;
CREATE SEQUENCE "otp_totp_totpdevice_id_seq";
ALTER TABLE "otp_totp_totpdevice" ALTER COLUMN "id" SET DEFAULT nextval('"otp_totp_totpdevice_id_seq"');
SELECT setval('"otp_totp_totpdevice_id_seq"', MAX("id")) FROM "otp_totp_totpdevice";
ALTER SEQUENCE "otp_totp_totpdevice_id_seq" OWNED BY "otp_totp_totpdevice"."id";
