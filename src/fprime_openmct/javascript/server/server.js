/**
 * Basic implementation of a history and realtime server.
 */
// Imports of other modules
const fs = require('fs');
const ZmqDataRetriever = require('./zmq-bridge');
const RealtimeServer = require('./realtime-server');
const StaticServer = require('./static-server');

// Basic argument specification
let arg_spec = {
    positional: [],
    flags: {},
    flag_key: null
};

// Process the command line arguments into a arg_spec object
process.argv.forEach((arg) =>{
    // Flag detected, no key. Set and move on 
    if (arg.indexOf("--") === 0) {
        arg_spec.flag_key = arg;
        arg_spec.flags[arg_spec.flag_key] = true; // Assume flag is true until a value is provided
    }
    // Key set, not flag, so store arg and reset key
    else if (arg_spec.flag_key !== null) {
        arg_spec.flags[arg_spec.flag_key] = arg;
        arg_spec.flag_key = null;
    }
    // No flag or key, so store arg as a positional
    else if (arg_spec.flag_key === null) {
        arg_spec.positional.push(arg);
    }
    // Algorithm error, assert
    else {
        console.assert(false, "Invalid argument parsing state");
    }
});

let help = () => {
    console.log("Usage: node server.js [--help] [--openmct-port <port>] [--openmct-dictionary <dictionary>]");
    console.log("  --help, -h: Show this help message");
    console.log("  --openmct-port: Port to run the server on (default: 8080)");
    console.log("  --openmct-dictionary: Path to the dictionary file (default: ./dictionary.json)");
};

// Read command line arguments
let port = arg_spec.flags['--openmct-port'] || 8080;
let dictionary = arg_spec.flags['--openmct-dictionary'] || './dictionary.json';
if (arg_spec.flags['--help'] || arg_spec.flags['-h']) {
    help();
    process.exit(0);
}
else if (!fs.existsSync(dictionary)) {
    console.error(`[ERROR] [Server] Dictionary file ${dictionary} does not exist`);
    help();
    process.exit(1);
}

console.log(`[INFO] [Server] Starting server on port ${port} with dictionary ${dictionary}`);

// Get an express app with WebSocket support
let expressWs = require('express-ws');
let app = require('express')();
expressWs(app);

// Instantiate the data-bridge
let dataReceiver = new ZmqDataRetriever("ipc:///tmp/fprime-openmct-push");

// Instantiate the static and realtime servers registering the express app
let staticServer = new StaticServer(dictionary);
let realtimeServer = new RealtimeServer(dataReceiver);
app.use('/realtime', realtimeServer.getRouter());
app.use('/', staticServer);

app.listen(port, function () {
    console.log(`[INFO] [Express] Open MCT hosted at http://localhost:${port}`);
    console.log(`[INFO] [Express] Realtime hosted at ws://localhost:${port}`);
});
dataReceiver.run();
