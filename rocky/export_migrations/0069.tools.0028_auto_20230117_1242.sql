--
-- Alter field organization on organizationmember
--
--
-- Alter field user on organizationmember
--
SET CONSTRAINTS "tools_organizationmember_user_id_c135c874_fk_account_katuser_id" IMMEDIATE; ALTER TABLE "tools_organizationmember" DROP CONSTRAINT "tools_organizationmember_user_id_c135c874_fk_account_katuser_id";
CREATE INDEX "tools_organizationmember_user_id_c135c874" ON "tools_organizationmember" ("user_id");
ALTER TABLE "tools_organizationmember" ADD CONSTRAINT "tools_organizationmember_user_id_c135c874_fk_account_katuser_id" FOREIGN KEY ("user_id") REFERENCES "account_katuser" ("id") DEFERRABLE INITIALLY DEFERRED;
--
-- Alter unique_together for organizationmember (1 constraint(s))
--
ALTER TABLE "tools_organizationmember" ADD CONSTRAINT "tools_organizationmember_user_id_organization_id_166e67c4_uniq" UNIQUE ("user_id", "organization_id");
--
-- Remove field goal from organizationmember
--
ALTER TABLE "tools_organizationmember" DROP COLUMN "goal" CASCADE;
--
-- Remove field member_role from organizationmember
--
ALTER TABLE "tools_organizationmember" DROP COLUMN "member_role" CASCADE;
--
-- Remove field signal_username from organizationmember
--
ALTER TABLE "tools_organizationmember" DROP COLUMN "signal_username" CASCADE;