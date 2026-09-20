#!/bin/sh
set -eu
# Valores passados como variáveis psql, escapados como literais SQL.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=graos_password="$GRAOS_DB_PASSWORD" \
  --set=metodo_password="$METODO_DB_PASSWORD" \
  --set=degustacao_password="$DEGUSTACAO_DB_PASSWORD" <<'SQL'
CREATE USER graos WITH PASSWORD :'graos_password';
CREATE USER metodo WITH PASSWORD :'metodo_password';
CREATE USER degustacao WITH PASSWORD :'degustacao_password';
CREATE DATABASE graos OWNER graos;
CREATE DATABASE metodo OWNER metodo;
CREATE DATABASE degustacao OWNER degustacao;
REVOKE CONNECT ON DATABASE graos FROM PUBLIC;
REVOKE CONNECT ON DATABASE metodo FROM PUBLIC;
REVOKE CONNECT ON DATABASE degustacao FROM PUBLIC;
GRANT CONNECT ON DATABASE graos TO graos;
GRANT CONNECT ON DATABASE metodo TO metodo;
GRANT CONNECT ON DATABASE degustacao TO degustacao;
SQL
