--
-- Create model FailureModeEffect
--
CREATE TABLE "fmea_failuremodeeffect" ("id" bigserial NOT NULL PRIMARY KEY, "effect" text NOT NULL UNIQUE, "severity_level" smallint NOT NULL CHECK ("severity_level" >= 0));
--
-- Remove field severity_level from failuremode
--
ALTER TABLE "fmea_failuremode" DROP COLUMN "severity_level" CASCADE;
--
-- Add field critical_score to failuremode
--
ALTER TABLE "fmea_failuremode" ADD COLUMN "critical_score" smallint DEFAULT 0 NOT NULL CHECK ("critical_score" >= 0);
ALTER TABLE "fmea_failuremode" ALTER COLUMN "critical_score" DROP DEFAULT;
--
-- Add field risk_priority_number to failuremode
--
ALTER TABLE "fmea_failuremode" ADD COLUMN "risk_priority_number" smallint DEFAULT 0 NOT NULL CHECK ("risk_priority_number" >= 0);
ALTER TABLE "fmea_failuremode" ALTER COLUMN "risk_priority_number" DROP DEFAULT;
--
-- Remove field effect from failuremode
--
ALTER TABLE "fmea_failuremode" DROP COLUMN "effect" CASCADE;
--
-- Add field effect to failuremode
--
CREATE TABLE "fmea_failuremode_effect" ("id" bigserial NOT NULL PRIMARY KEY, "failuremode_id" bigint NOT NULL, "failuremodeeffect_id" bigint NOT NULL);
CREATE INDEX "fmea_failuremodeeffect_effect_6c4db27b_like" ON "fmea_failuremodeeffect" ("effect" text_pattern_ops);
ALTER TABLE "fmea_failuremode_effect" ADD CONSTRAINT "fmea_failuremode_effect_failuremode_id_failuremo_49edaaa8_uniq" UNIQUE ("failuremode_id", "failuremodeeffect_id");
ALTER TABLE "fmea_failuremode_effect" ADD CONSTRAINT "fmea_failuremode_eff_failuremode_id_909aa382_fk_fmea_fail" FOREIGN KEY ("failuremode_id") REFERENCES "fmea_failuremode" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "fmea_failuremode_effect" ADD CONSTRAINT "fmea_failuremode_eff_failuremodeeffect_id_3f227a6a_fk_fmea_fail" FOREIGN KEY ("failuremodeeffect_id") REFERENCES "fmea_failuremodeeffect" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "fmea_failuremode_effect_failuremode_id_909aa382" ON "fmea_failuremode_effect" ("failuremode_id");
CREATE INDEX "fmea_failuremode_effect_failuremodeeffect_id_3f227a6a" ON "fmea_failuremode_effect" ("failuremodeeffect_id");