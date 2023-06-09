-- Since encryption/decryption happens at the application level but these migrations do not use alembic,
-- follow the instructions below to ensure no data is lost.

CREATE TABLE settings (
    id SERIAL NOT NULL,
    values VARCHAR(512) NOT NULL,
    plugin_id VARCHAR(64) NOT NULL,
    organisation_pk INTEGER NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(organisation_pk) REFERENCES organisation (pk) ON DELETE CASCADE,
    CONSTRAINT unique_settings_per_organisation_per_plugin UNIQUE (organisation_pk, plugin_id)
);

-- IMPORTANT: before dropping the old setting table, migrate the old data in one of the following ways:

-- When no encryption had been set up yet, this query can seed the new table with old values:
    -- INSERT INTO settings (values, plugin_id, organisation_pk) SELECT json_object_agg(key, value)
    -- AS values, plugin_id, organisation_pk FROM setting GROUP BY organisation_pk, plugin_id;

-- If settings were encrypted, this should fill the new table with old settings (cwd being nl-kat-coordination/boefjes):
    -- python -m boefjes.migrations.versions.cd34fdfafdaf_json_settings_for_settings_table

DROP TABLE setting;
