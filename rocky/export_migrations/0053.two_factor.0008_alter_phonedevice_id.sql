--
-- Alter field id on phonedevice
--
ALTER TABLE "two_factor_phonedevice" ALTER COLUMN "id" TYPE bigint USING "id"::bigint;
DROP SEQUENCE IF EXISTS "two_factor_phonedevice_id_seq" CASCADE;
CREATE SEQUENCE "two_factor_phonedevice_id_seq";
ALTER TABLE "two_factor_phonedevice" ALTER COLUMN "id" SET DEFAULT nextval('"two_factor_phonedevice_id_seq"');
SELECT setval('"two_factor_phonedevice_id_seq"', MAX("id")) FROM "two_factor_phonedevice";
ALTER SEQUENCE "two_factor_phonedevice_id_seq" OWNED BY "two_factor_phonedevice"."id";