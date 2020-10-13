# Do this every time you change the type:
DROP TYPE exposure_flag_type;
CREATE TYPE exposure_flag_type as ENUM('junk', 'questionable');

# Do this every time you change the schema:
DROP TABLE owl_messages;
CREATE TABLE owl_messages(
    id SERIAL PRIMARY KEY,
    obs_id VARCHAR NOT NULL,
    instrument VARCHAR NOT NULL,
    day_obs INTEGER NOT NULL,
    message_text TEXT NOT NULL,
    user_id VARCHAR NOT NULL,
    user_agent VARCHAR NOT NULL,
    is_human BOOL NOT NULL,
    is_valid BOOL NOT NULL,
    exposure_flag exposure_flag_type,
    date_added TIMESTAMP NOT NULL,
    date_is_valid_changed TIMESTAMP,
    parent_id BIGINT
);
CREATE INDEX ON owl_messages(obs_id);
CREATE INDEX ON owl_messages(instrument);
CREATE INDEX ON owl_messages(day_obs);
CREATE INDEX ON owl_messages(user_id);
CREATE INDEX ON owl_messages(user_agent);
CREATE INDEX ON owl_messages(is_human);
CREATE INDEX ON owl_messages(is_valid);
CREATE INDEX ON owl_messages(exposure_flag);
