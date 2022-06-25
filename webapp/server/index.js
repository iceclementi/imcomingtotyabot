const express = require( "express" );
const cors = require( "cors" );
// const pool = require( "./db" );
const PORT = 5000;

const app = express();
app.use( cors() );
app.use( express.json() );

app.listen( PORT, () => {
	console.log( `Server is starting on port ${ PORT }` );
} );
