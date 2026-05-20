-- Initialisation MySQL/Galera pour SUPFile (à exécuter une seule fois).
-- Exemple:
-- mysql -h 10.10.1.32 -P 6033 -u admin -p < backend/scripts/init_galera_schema.sql

CREATE DATABASE IF NOT EXISTS supfile
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'supfile_app'@'%' IDENTIFIED BY 'CHANGE_ME_STRONG_PASSWORD';

GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, INDEX, REFERENCES
ON supfile.* TO 'supfile_app'@'%';

FLUSH PRIVILEGES;
