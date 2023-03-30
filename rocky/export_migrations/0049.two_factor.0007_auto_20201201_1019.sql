--
-- Add field throttling_failure_count to phonedevice
--
ALTER TABLE "two_factor_phonedevice" ADD COLUMN "throttling_failure_count" integer DEFAULT 0 NOT NULL CHECK ("throttling_failure_count" >= 0);
ALTER TABLE "two_factor_phonedevice" ALTER COLUMN "throttling_failure_count" DROP DEFAULT;
--
-- Add field throttling_failure_timestamp to phonedevice
--
ALTER TABLE "two_factor_phonedevice" ADD COLUMN "throttling_failure_timestamp" timestamp with time zone NULL;
