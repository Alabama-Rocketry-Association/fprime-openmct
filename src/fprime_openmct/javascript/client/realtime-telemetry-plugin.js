/**
 * Basic Realtime telemetry plugin using websockets.
 */
function RealtimeTelemetryPlugin() {
    return function (openmct) {
        try {
            let socket = new WebSocket(location.origin.replace(/^http/, 'ws') + '/realtime/');
            let listener = {};
            let message_queue = {
                queue: [],
                active: true
            }

            /**
             * WebSockets might not be set up immediately, thus queued messages must be sent down.
             * @param {*} event: onopen event
             */
            socket.onopen = function(event) {
                try {
                    // Drain the message queue and deactivate onopen
                    if (message_queue.active) {
                        message_queue.queue.forEach((message) => socket.send(message));
                        message_queue.active = false;
                    }
                } catch(e) {
                    console.log("[ERROR] Failed to drain messages on open.", e);
                }
            }

            /**
             * Function to handle incoming messages
             * 
             * When an incoming data message arrives, it calls the the callback registered with the listener or
             * discards the message.
             * 
             * @param {*} event: event received
             */
            socket.onmessage = function (event) {
                try {
                    let data = JSON.parse(event.data);
                    for (let i = 0; i < data.length; i++) {
                        if (listener[data[i].key]) {
                            listener[data[i].key](data[i]);
                        }
                    }
                } catch (e) {
                    console.error("[ERROR] Received bad message.", e);
                }
            };

            let provider = {
                /**
                 * Determine if the domain object type is provided by this data provider
                 * 
                 * This provider will work for all 'fprime.channel' types. When 'true' is returned a subsequent call to
                 * the subscribe function will perform the actual subscription.
                 * 
                 * @param {*} domainObject: domainObject to test
                 * @returns true when it will provide, false when not
                 */
                supportsSubscribe: function (domainObject) {
                    return domainObject.type === 'fprime.channel';
                },
                /**
                 * Subscribe to a given data stream
                 * 
                 * This will subscribe to a given data stream using the message 'subscribe <telemetry key>'. It returns
                 * a function used to unsubscribe.
                 * 
                 * @param {*} domainObject: object used for subscription key
                 * @param {*} callback: function to call with incoming data objects
                 * @returns: unsubscribe function
                 */
                subscribe: function (domainObject, callback) {
                    try {
                        listener[domainObject.identifier.key] = callback;
                        return () => {
                            delete listener[domainObject.identifier.key];
                        };
                    } catch (e) {
                        console.error("[ERROR] Failed to subscribe", e);
                    }
                }
            };
            openmct.telemetry.addProvider(provider);
        } catch (e) {
            console.error("[ERROR] Failed to set up websockets based provider.", e);
        }
    }
}
