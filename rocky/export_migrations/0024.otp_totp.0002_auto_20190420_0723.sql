--
-- Add field throttling_failure_count to totpdevice
--
ALTER TABLE "otp_totp_totpdevice" ADD COLUMN "throttling_failure_count" integer DEFAULT 0 NOT NULL CHECK ("throttling_failure_count" >= 0);
ALTER TABLE "otp_totp_totpdevice" ALTER COLUMN "throttling_failure_count" DROP DEFAULT;
--
-- Add field throttling_failure_timestamp to totpdevice
--
ALTER TABLE "otp_totp_totpdevice" ADD COLUMN "throttling_failure_timestamp" timestamp with time zone NULL;