--
-- Create model FailureMode
--
CREATE TABLE "fmea_failuremode" ("id" bigserial NOT NULL PRIMARY KEY, "failure_mode" varchar(256) NOT NULL, "severity_level" smallint NOT NULL CHECK ("severity_level" >= 0), "frequency_level" smallint NOT NULL CHECK ("frequency_level" >= 0), "detectability_level" smallint NOT NULL CHECK ("detectability_level" >= 0), "risk_class" varchar(50) NULL, "effect" varchar(256) NOT NULL, "description" varchar(256) NOT NULL);
--
-- Create model FailureModeDepartment
--
CREATE TABLE "fmea_failuremodedepartment" ("id" bigserial NOT NULL PRIMARY KEY, "affected_department" smallint NOT NULL CHECK ("affected_department" >= 0), "failure_mode_id" bigint NULL);
ALTER TABLE "fmea_failuremodedepartment" ADD CONSTRAINT "fmea_failuremodedepa_failure_mode_id_2e3d3d4b_fk_fmea_fail" FOREIGN KEY ("failure_mode_id") REFERENCES "fmea_failuremode" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "fmea_failuremodedepartment_failure_mode_id_2e3d3d4b" ON "fmea_failuremodedepartment" ("failure_mode_id");
