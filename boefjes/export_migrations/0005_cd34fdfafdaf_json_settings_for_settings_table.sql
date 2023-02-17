CREATE TABLE settings (
    id SERIAL NOT NULL, 
    values JSON NOT NULL, 
    plugin_id VARCHAR(64) NOT NULL, 
    organisation_pk INTEGER NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(organisation_pk) REFERENCES organisation (pk) ON DELETE CASCADE, 
    CONSTRAINT unique_settings_per_organisation_per_plugin UNIQUE (organisation_pk, plugin_id)
);

INSERT INTO settings (values, plugin_id, organisation_pk) SELECT json_object_agg(key, value) AS values, plugin_id, organisation_pk FROM setting GROUP BY organisation_pk, plugin_id;

DROP TABLE setting;

