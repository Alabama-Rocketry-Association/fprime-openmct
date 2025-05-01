// Dictionary is provided via a known web-endpoint
let DICTIONARY_URL_PATH = "/dictionary.json";

function postProcessDictionary(dictionary_data) {
    let deployment_name = dictionary_data.name.replace("TopologyDictionary", "");
    let namespace = `fprime.${deployment_name}`.toLowerCase();
    let objects_index = {
        "fprime": {},
    };
    objects_index[namespace] = {};

    // Channels are determined from measurements
    let unique_channels = dictionary_data.measurements.map((measurement) => {
        let split_on_dot = (measurement.origin || measurement.key).split(".")
        console.assert(split_on_dot.length >= 2, "Measurement did not include at least component and channel");
        return {
            fprime_type: "channel",
            name: measurement.name,
            key: measurement.key,
            namespace: namespace,
            deployment: deployment_name,
            subtopology: split_on_dot.slice(0, -2).join("."),
            component: split_on_dot.slice(0, -1).join("."),
            measurement: measurement
        }
    });
    // Index channels
    unique_channels.forEach((item) => {objects_index[item.namespace][item.key] = item});

    // Components are composed of channels
    let unique_components = [...new Set(unique_channels.map(
        (item) => JSON.stringify({
            fprime_type: "component",
            key: item.component,
            name: `${item.component} [Component]`,
            namespace: namespace,
            deployment: deployment_name,
            subtopology: item.subtopology,
            children: unique_channels.filter((channel) => channel.component == item.component)
        })
    ))].map((item) => JSON.parse(item));
    // Index components
    unique_components.forEach((item) => {objects_index[item.namespace][item.key] = item});

    // Subtopologies are composed of multiple components
    let unique_subtopologies = [...new Set(unique_components.map(
        (item) => JSON.stringify({
            fprime_type: "subtopology",
            key: item.subtopology,
            name: `${item.subtopology} [Subtopology]`,
            namespace: namespace,
            deployment: deployment_name,
            children: unique_components.filter((component) => component.subtopology == item.subtopology)
        })
    ))].map((item) => JSON.parse(item));
    // Index subtopologies
    unique_subtopologies.forEach((item) => {objects_index[item.namespace][item.key] = item});

    // Final structure of a single dictionary: deployment
    //   composed of multiple subtopologies
    //     each composed of multiple components
    //       each composed of multiple channels
    let deployment = {
        fprime_type: "deployment",
        key: deployment_name,
        name: `${deployment_name} [Deployment]`,
        namespace: "fprime",
        children: unique_subtopologies
    }
    // Index deployment
    dictionary_data.deployment = deployment;
    dictionary_data.namespace = namespace;
    objects_index["fprime"][deployment_name] = deployment;
    dictionary_data.objects_index = objects_index;
    return dictionary_data;
}

function getDictionaries() {
    let _self = this;
    if (_self.dictionaries) {
        return new Promise((resolve, reject) => resolve(_self.dictionaries));
    }
    return http.get(DICTIONARY_URL_PATH)
        .then(function (result) {
            _self.dictionaries = [postProcessDictionary(result.data)];
            return _self.dictionaries;
        });
}

function getDictionaryForIdentifier(dictionaries, identifier) {
    // Deployments live in the "fprime" namespace, other objects live in fprime.${ deployment } namespaces
    let matching_dictionaries = dictionaries.filter(
        (dictionary) => (identifier.namespace == "fprime" && identifier.key == dictionary.deployment.key) ||
                        (dictionary.namespace == identifier.namespace)
    );
    console.assert(matching_dictionaries.length == 1, `Found ${matching_dictionaries.length} dictionaries, expected 1`);
    return matching_dictionaries[0];
}


function getEntryForIdentifier(dictionary, identifier) {
    let object_entry = dictionary.objects_index[identifier.namespace][identifier.key];
    console.assert(object_entry, `Unable lo locate  '${identifier.namespace}:${identifier.key}' in dictionary`);
    return object_entry;
}

let objectProvider = {
    get: function (identifier) {
        // Load the dictionary and respond with specific results
        return getDictionaries().then(function (dictionaries) {
            // Catch and log errors internally
            try {
                // "project" is the top-level node, respond with a "ROOT" item
                if (identifier.key === "project") {
                    return {
                        identifier: identifier,
                        name: "project",
                        type: 'folder',
                        location: 'ROOT'
                    };
                }
                let dictionary = getDictionaryForIdentifier(dictionaries, identifier);
                let object_entry = getEntryForIdentifier(dictionary, identifier);

                let parent_namespace = (object_entry.fprime_type === "deployment") ?
                                        "fprime" : `fprime.${object_entry.deployment}`.toLocaleLowerCase();
                let parent_name = object_entry.component ||
                                  object_entry.subtopology ||
                                  object_entry.deployment ||
                                  "project";
                let location = `${parent_namespace}:${parent_name}`;
                let object_source = {};
                // Anything with children is folder type
                if (typeof(object_entry.children) !== "undefined") {
                    object_source = {
                        identifier: identifier,
                        name: object_entry.name,
                        type: 'folder',
                        location: location,
                    };
                }
                else {
                    object_source = {
                        identifier: identifier,
                        name: object_entry.name,
                        type: 'fprime.channel',
                        telemetry: {
                            values: object_entry.measurement.values
                        },
                        location: location
                    };
                }
                return object_source;
            } catch (e) {
                console.log(`[ERROR] [F´] Provision failed for: ${identifier.namespace}:${identifier.key}. ${e}`);
            }
            return {}
        });
    }
};
/**
 * The composition provider determines what an identifier is composed of.
 */
var compositionProvider = {
    appliesTo: function (domainObject) {
        return domainObject.identifier.namespace.indexOf('fprime') == 0 &&
               domainObject.type === 'folder';
    },
    load: function (domainObject) {
        return new getDictionaries().then(function (dictionaries) {
            // OpenMCT seems to catch and mask errors, so we will trap and log internally
            try {
                let identifier = domainObject.identifier || {}; 

                // Projects have 1-N deployments each with a dictionary
                if (identifier.key == "project") {
                    return dictionaries.map((dictionary) => {
                        return {
                            namespace: "fprime",
                            key: dictionary.deployment.key,
                            fprime_type: "deployment"
                        }
                    });
                }
                let dictionary = getDictionaryForIdentifier(dictionaries, identifier);
                let object_entry = getEntryForIdentifier(dictionary, identifier);

                // Composition uses the child property
                let compositions =  (object_entry.children || []).map((child) => {
                    return {
                        namespace: child.namespace,
                        key: child.key
                    }
                });
                return compositions;
            } catch (e) {
                console.log(`[ERROR] [F´] Composition failed for: ${identifier.namespace}:${identifier.key}. ${e}`);
            }
            return [];
        });
    }
};

var DictionaryPlugin = function (openmct) {
    return function install(openmct) {
        // Each root node is in the fprime.taxonomy namespace keyed to the deployment name
        openmct.objects.addRoot({
            namespace: "fprime",
            key: "project"
        });
        // Use the provided object provider for the 'fprime' namespace and all namespace loaded in our dictionaries
        openmct.objects.addProvider('fprime', objectProvider);
        openmct.objects.addProvider('fprime.ref', objectProvider);
        getDictionaries().then((dictionaries) => {
            dictionaries.forEach((dictionary) => {
                openmct.objects.addProvider(dictionary.deployment.namespace, objectProvider);
            })
        });

        // Composition provider
        openmct.composition.addProvider(compositionProvider);

        // Add in an fprime type for telemetry channels
        openmct.types.addType('fprime.channel', {
            name: 'F Prime Telemetry Channel',
            description: 'Telemetry Channel Reading Generated from F Prime',
            cssClass: 'icon-telemetry'
        });
    }
};
