--
-- Create model FailureModeAffectedObject
--
CREATE TABLE "fmea_failuremodeaffectedobject" ("id" bigserial NOT NULL PRIMARY KEY, "affected_department" varchar(50) NOT NULL, "affected_ooi_type" varchar(100) NOT NULL);
--
-- Create model FailureModeTreeObject
--
CREATE TABLE "fmea_failuremodetreeobject" ("id" bigserial NOT NULL PRIMARY KEY, "tree_object" varchar(256) NOT NULL, "affected_department" varchar(50) NOT NULL);
--
-- Alter field detectability_level on failuremode
--
--
-- Alter field failure_mode on failuremode
--
ALTER TABLE "fmea_failuremode" ADD CONSTRAINT "fmea_failuremode_failure_mode_92f39c8f_uniq" UNIQUE ("failure_mode");
CREATE INDEX "fmea_failuremode_failure_mode_92f39c8f_like" ON "fmea_failuremode" ("failure_mode" varchar_pattern_ops);
--
-- Alter field frequency_level on failuremode
--
--
-- Alter field severity_level on failuremode
--
--
-- Delete model FailureModeDepartment
--
DROP TABLE "fmea_failuremodedepartment" CASCADE;
--
-- Add field failure_mode to failuremodeaffectedobject
--
ALTER TABLE "fmea_failuremodeaffectedobject" ADD COLUMN "failure_mode_id" bigint NULL CONSTRAINT "fmea_failuremodeaffe_failure_mode_id_4fec46e6_fk_fmea_fail" REFERENCES "fmea_failuremode"("id") DEFERRABLE INITIALLY DEFERRED; SET CONSTRAINTS "fmea_failuremodeaffe_failure_mode_id_4fec46e6_fk_fmea_fail" IMMEDIATE;
CREATE INDEX "fmea_failuremodeaffectedobject_failure_mode_id_4fec46e6" ON "fmea_failuremodeaffectedobject" ("failure_mode_id");
