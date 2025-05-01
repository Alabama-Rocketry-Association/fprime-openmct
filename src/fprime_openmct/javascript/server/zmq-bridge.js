/**
 * @file server/zmq-bridge.js: ZeroMQ bridge to fprime-openmct's data handler plugin.
 */
const zmq = require('zeromq');
/**
 * Connects to the fprime-openmct data handler plugin via ZeroMQ and forwards the received data to the OpenMCT client
 * via the registered "onReceive" callback.
 */
class ZmqDataRetriever {
    /**
     * Constructor for the ZmqDataRetriever. Sets up the ZeroMQ subscriber.
     * with the data provider.
     * 
     * @param {string} connection_string: ZeroMQ connection string to the fprime-openmct data handler plugin
     */
    constructor(connection_string) {
        this.socket = new zmq.Subscriber();
        this.socket.connect(connection_string);
        this.socket.subscribe("fprime-openmct"); // Subscribe to "fprime-openmct" messages
        this.onReceive = null;
    }

    /**
     * Sets the callback that is called when data is received from the ZeroMQ socket.
     * @param {function} callback: Callback function that is called when data is received
     */
    onReceive(callback) {
        this.onReceive = callback;
    }

    /**
     * Run method that listens for incoming messages from the ZeroMQ socket and forwards them to the registered
     * "onReceive" callback.
     */
    async run() {
        for await (const [topic, raw_json] of this.socket) {
            let data = JSON.parse(raw_json.toString());
            if (this.onReceive != null) {
                this.onReceive(data);
            }
        }
    }

    /**
     * Closes the ZeroMQ socket.
     */
    close() {
        this.onReceive = null;
        this.socket.close();
    }

}

module.exports = ZmqDataRetriever;