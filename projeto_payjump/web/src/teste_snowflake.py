import snowflake.connector

conn = snowflake.connector.connect(
    account = "SUPREMA-DATA_TEAM",
    user = "DOUGLAS_FERREIRA",
    authenticator = "externalbrowser",
    role = "SECURITY_TEAM_ROLE",
    warehouse = "<none selected>",
    database = "SECURITY",
    schema = "NRT_V2"
    )

print('Conexão bem sucessida.')
conn.close()