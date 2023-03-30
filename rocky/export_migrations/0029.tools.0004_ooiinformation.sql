--
-- Create model OOIInformation
--
CREATE TABLE "tools_ooiinformation" ("id" varchar(256) NOT NULL PRIMARY KEY, "last_updated" timestamp with time zone NOT NULL, "data" jsonb NULL, "consult_api" boolean NOT NULL);
CREATE INDEX "tools_ooiinformation_id_a78335b7_like" ON "tools_ooiinformation" ("id" varchar_pattern_ops);
