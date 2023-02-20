-- Since encryption/decryption happens at the application level, it is much preferred to run migrations through
-- alembic to not lose any previously defined settings.

CREATE TABLE settings (
    id SERIAL NOT NULL,
    values VARCHAR(512) NOT NULL,
    plugin_id VARCHAR(64) NOT NULL,
    organisation_pk INTEGER NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(organisation_pk) REFERENCES organisation (pk) ON DELETE CASCADE,
    CONSTRAINT unique_settings_per_organisation_per_plugin UNIQUE (organisation_pk, plugin_id)
);

-- When no encryption had been set up yet, this query can seed the new table with unencrypted old values:

-- INSERT INTO settings (values, plugin_id, organisation_pk) SELECT json_object_agg(key, value)
-- AS values, plugin_id, organisation_pk FROM setting GROUP BY organisation_pk, plugin_id;

DROP TABLE setting;
