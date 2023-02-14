--
-- Create model ScanProfile
--
CREATE TABLE "tools_scanprofile" ("id" bigserial NOT NULL PRIMARY KEY, "reference" varchar(256) NOT NULL, "level" smallint NOT NULL CHECK ("level" >= 0), "new" boolean NOT NULL, "organization_id" bigint NOT NULL, "user_id" integer NULL);
ALTER TABLE "tools_scanprofile" ADD CONSTRAINT "tools_scanprofile_reference_organization_id_fade857c_uniq" UNIQUE ("reference", "organization_id");
ALTER TABLE "tools_scanprofile" ADD CONSTRAINT "tools_scanprofile_organization_id_de0a262e_fk_tools_org" FOREIGN KEY ("organization_id") REFERENCES "tools_organization" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "tools_scanprofile" ADD CONSTRAINT "tools_scanprofile_user_id_6a9bb1d5_fk_auth_user_id" FOREIGN KEY ("user_id") REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "tools_scanprofile_organization_id_de0a262e" ON "tools_scanprofile" ("organization_id");
CREATE INDEX "tools_scanprofile_user_id_6a9bb1d5" ON "tools_scanprofile" ("user_id");