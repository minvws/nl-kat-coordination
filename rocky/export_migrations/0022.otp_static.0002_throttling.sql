--
-- Add field throttling_failure_count to staticdevice
--
ALTER TABLE "otp_static_staticdevice" ADD COLUMN "throttling_failure_count" integer DEFAULT 0 NOT NULL CHECK ("throttling_failure_count" >= 0);
ALTER TABLE "otp_static_staticdevice" ALTER COLUMN "throttling_failure_count" DROP DEFAULT;
--
-- Add field throttling_failure_timestamp to staticdevice
--
ALTER TABLE "otp_static_staticdevice" ADD COLUMN "throttling_failure_timestamp" timestamp with time zone NULL;