const pg = require("pg");
const Pool = pg.Pool;

const pool = new Pool({
	user: "postgres",
	password: "password",
	database: "test_database",
	host: "localhost",
	port: 5432
})

module.exports = pool;
