/**
 * @file server/static-server.js: host the static HTML/JS/CSS files used for our OpenMCT bridge
 * @author: lestarch
 * 
 * This fill will host the index.html, and various JavaScript client files needed for index.html
 */
let express = require('express');

/**
 * Set up the static server
 * @param {Object} app - the express app
 * @returns: express.Router() - the router for the static server
 */
function StaticServer(dictionary) {
    let router = express.Router();

    router.use('/', express.static(__dirname + '/..'));
    router.use('/dictionary.json', express.static(dictionary));
    return router;
}

module.exports = StaticServer;
