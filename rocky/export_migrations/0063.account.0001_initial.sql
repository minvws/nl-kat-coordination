--
-- Switching to custom user model
--
-- NOTHING TO DO BECAUSE TABLES WERE ALREADY CREATED
--
-- Rename model User to KATUser
--
ALTER TABLE "auth_user_groups" RENAME COLUMN "user_id" TO "katuser_id";
ALTER TABLE "auth_user_user_permissions" RENAME COLUMN "user_id" TO "katuser_id";
--
-- Change Meta options on katuser
--
--
-- Rename table for katuser to (default)
--
ALTER TABLE "auth_user" RENAME TO "account_katuser";
ALTER TABLE "auth_user_groups" RENAME TO "account_katuser_groups";
ALTER TABLE "auth_user_user_permissions" RENAME TO "account_katuser_user_permissions";
--
-- Raw SQL operation
--
ALTER INDEX auth_user_pkey RENAME TO account_katuser_pkey;
ALTER INDEX auth_user_groups_pkey RENAME TO account_katuser_groups_pkey;
ALTER INDEX auth_user_user_permissions_pkey RENAME TO account_katuser_user_permissions_pkey;
ALTER SEQUENCE auth_user_id_seq RENAME TO account_katuser_id_seq;
ALTER SEQUENCE auth_user_groups_id_seq RENAME TO account_katuser_groups_id_seq;
ALTER SEQUENCE auth_user_user_permissions_id_seq RENAME TO account_katuser_user_permissions_id_seq;
--
-- Raw Python operation
--
ALTER INDEX auth_user_groups_group_id_97559544 RENAME TO account_katuser_groups_group_id_458b8cb6;
ALTER INDEX auth_user_groups_user_id_6a12ed8b RENAME TO account_katuser_groups_katuser_id_f4516588;
ALTER INDEX public.auth_user_user_permissions_permission_id_1fbb5f2c RENAME TO account_katuser_user_permissions_permission_id_7a0ee5f4;
ALTER INDEX public.auth_user_user_permissions_user_id_a95ead1b RENAME TO account_katuser_user_permissions_katuser_id_b66fdc16;
ALTER TABLE public.account_katuser_groups RENAME CONSTRAINT auth_user_groups_user_id_group_id_94350c0c_uniq TO account_katuser_groups_katuser_id_group_id_1cb4bafd_uniq;
ALTER TABLE public.account_katuser_groups RENAME CONSTRAINT auth_user_groups_group_id_97559544_fk_auth_group_id TO account_katuser_groups_group_id_458b8cb6_fk_auth_group_id;
ALTER TABLE public.account_katuser_groups RENAME CONSTRAINT auth_user_groups_user_id_6a12ed8b_fk_auth_user_id TO account_katuser_grou_katuser_id_f4516588_fk_account_k;
ALTER TABLE public.account_katuser_user_permissions RENAME CONSTRAINT auth_user_user_permissions_user_id_permission_id_14a6b632_uniq TO account_katuser_user_per_katuser_id_permission_id_10f2db9d_uniq;
ALTER TABLE public.account_katuser_user_permissions RENAME CONSTRAINT auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm TO account_katuser_user_permission_id_7a0ee5f4_fk_auth_perm;
ALTER TABLE public.account_katuser_user_permissions RENAME CONSTRAINT auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id TO account_katuser_user_katuser_id_b66fdc16_fk_account_k;
ALTER TABLE public.django_admin_log RENAME CONSTRAINT django_admin_log_user_id_c564eba6_fk_auth_user_id TO django_admin_log_user_id_c564eba6_fk_account_katuser_id;
ALTER TABLE public.otp_static_staticdevice RENAME CONSTRAINT otp_static_staticdevice_user_id_7f9cff2b_fk_auth_user_id TO otp_static_staticdevice_user_id_7f9cff2b_fk_account_katuser_id;
ALTER TABLE public.otp_totp_totpdevice RENAME CONSTRAINT otp_totp_totpdevice_user_id_0fb18292_fk_auth_user_id TO otp_totp_totpdevice_user_id_0fb18292_fk_account_katuser_id;
ALTER TABLE public.password_history_userpasswordhistoryconfig RENAME CONSTRAINT password_history_use_user_id_bc5676f2_fk_auth_user TO password_history_use_user_id_bc5676f2_fk_account_k;
ALTER TABLE public.tools_indemnification RENAME CONSTRAINT tools_indemnification_user_id_2e9bb970_fk_auth_user_id TO tools_indemnification_user_id_2e9bb970_fk_account_katuser_id;
ALTER TABLE public.tools_organizationmember RENAME CONSTRAINT tools_organizationmember_user_id_c135c874_fk_auth_user_id TO tools_organizationmember_user_id_c135c874_fk_account_katuser_id;
ALTER TABLE public.two_factor_phonedevice RENAME CONSTRAINT two_factor_phonedevice_user_id_54718003_fk_auth_user_id TO two_factor_phonedevice_user_id_54718003_fk_account_katuser_id;
--
--
-- Raw Python operation
--
--
UPDATE django_content_type SET app_label = 'account', model = 'katuser' WHERE app_label = 'auth' AND model = 'user';
UPDATE auth_permission SET codename='add_katuser', name = 'Can add kat user' WHERE codename = 'add_user';
UPDATE auth_permission SET codename='change_katuser', name = 'Can change kat user' WHERE codename = 'change_user';
UPDATE auth_permission SET codename='delete_katuser', name = 'Can delete kat user' WHERE codename = 'delete_user';
UPDATE auth_permission SET codename='view_katuser', name = 'Can view kat user' WHERE codename = 'view_user';
-- Change managers on katuser
--
--
-- Remove field username from katuser
--
ALTER TABLE "account_katuser" DROP COLUMN "username" CASCADE;
--
-- Add field full_name to katuser
--
ALTER TABLE "account_katuser" ADD COLUMN "full_name" varchar(150) DEFAULT '' NOT NULL;
ALTER TABLE "account_katuser" ALTER COLUMN "full_name" DROP DEFAULT;
--
-- Alter field email on katuser
--
ALTER TABLE "account_katuser" ADD CONSTRAINT "account_katuser_email_fb55e6b7_uniq" UNIQUE ("email");
CREATE INDEX "account_katuser_email_fb55e6b7_like" ON "account_katuser" ("email" varchar_pattern_ops);
--
-- MIGRATION NOW PERFORMS OPERATION THAT CANNOT BE WRITTEN AS SQL:
UPDATE account_katuser SET full_name = btrim(concat(first_name, ' ', last_name));
