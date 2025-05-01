/**
 * @file server/RealtimeServer.js: real-time server (WebSocket) for OpenMCT.
 */
let express = require('express');

/**
 * RealtimeServer that forwards data received to the WebSocket created by the OpenMCT client plugin.
 */
class RealtimeServer {
    /**
     * Constructor for the RealtimeServer. Registers an "onReceive" callback with the data provider and a WebSocket
     * route with the express app.
     * @param {*} dataProvider: Data provider that provides the data to be sent to OpenMCT 
     */
    constructor(dataProvider) {
        dataProvider.onReceive = this.dataCallback.bind(this);
        this.router = express.Router();
        this.router.ws('/', this.handleWebSocket.bind(this));
        this.ws = null;
    }
    /**
     * Return the express router for the RealtimeServer.
     * @returns: express.Router() - the router for the RealtimeServer
     */
    getRouter() {
        return this.router;
    }

    /**
     * Sets up the WebSocket binding.
     * @param {WebSocket} ws: WebSocket connection to the OpenMCT client 
     * @param {*} req: unused
     */
    handleWebSocket(ws, req) {
        let _self = this;
        console.log("[INFO] [DataServer] WebSocket connection established");
        ws.on('close', () => {_self.ws = null;});
        ws.on('message', (message) => {
            console.warn("[WARNING] [DataServer] Unexpected message from client: " + message);
        }); 
        this.ws = ws;
    }
    /**
     * Callback used for the "onReceive" event of the data provider.
     * @param {string} channel: JSON channelized data to send to OpenMCT 
     */
    dataCallback(channel) {
        if (this.ws != null) {
            this.ws.send(JSON.stringify(channel));
        }
    }
}

module.exports = RealtimeServer;
