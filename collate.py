import glob
import json
import csv
import os
import logging
import sys
import inflection
from botocore.session import get_session


def setup_logging(logger, verbosity=None):
    """Summary.

    Args:
        logger (TYPE): Description
        verbosity (None, optional): Description
    """
    import sys
    from colorlog import ColoredFormatter
    # from pythonjsonlogger import jsonlogger

    global log
    log = logger

    if verbosity is None:
        verbosity = logging.INFO

    if len(log.handlers) == 0:
        logging.basicConfig(filename='debug.log', level=verbosity)
        # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        formatter_console_colour = "%(log_color)s%(levelname)-8s %(module)s:%(lineno)d- %(name)s%(reset)s %(blue)s%(message)s"

        """
        # create kinesis handler
        # formatter_json = jsonlogger.JsonFormatter()
        q = queue.Queue()
        kinesis_handler = kinesishandler.KinesisHandler(10, q)
        kinesis_handler.setFormatter(formatter_json)
        kinesis_handler.setLevel(logging.INFO)
        worker = kinesishandler.Worker(
            q, "aws-account-base-stream", region="us-east-1")
        worker.start()
        log.addHandler(kinesis_handler)
        """

        # add std out handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(verbosity)
        colored_formatter = ColoredFormatter(
            formatter_console_colour,
            datefmt='%H:%M:%S ',
            reset=True,
            log_colors={
                'DEBUG': 'white',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'orange',
                'CRITICAL': 'red',
            }
        )
        console_handler.setFormatter(colored_formatter)
        log.addHandler(console_handler)
        log.debug("logging initialized")


log = logging.getLogger()
setup_logging(log, verbosity=logging.INFO)


f = csv.writer(open("test.csv", "w", newline=''))
f.writerow(["resource", "model", "codename", "name", "content_type"])

cfn = {}

spec = {
    "ResourceTypes": {},
    "PropertyTypes": {},
    "Docs2Resource": {}
}

spec["PropertyTypes"]["String"] = "example-string"
spec["PropertyTypes"]["Boolean"] = "True"
spec["PropertyTypes"]["Integer"] = "1"
spec["PropertyTypes"]["Long"] = "123.4"
spec["PropertyTypes"]["Double"] = "123.45"
spec["PropertyTypes"]["Float"] = "1.23456789"
spec["PropertyTypes"]["Json"] = {"todo": "json"}
spec["PropertyTypes"]["Timestamp"] = "1970-01-01T01:02:30.070Z"
spec["PropertyTypes"]["Tags"] = [
    {
        "Key": "keyName",
        "Value": "valueName"
    }
]

all_keys = set()
processed_selectors = {}


# MERGE ALL REGIONAL CFN SCHEMAS INTO SUPERSCHEMA WITH ENRICHMENT

for file in glob.glob("../../data/cfn_resource_specs/CloudFormationResourceSpecification-*.json"):
    log.debug(file)
    region = file.rstrip('.json').split(
        'CloudFormationResourceSpecification-')[1].lower().strip()
    log.debug(region)
    with open(file, 'r') as schema:
        cfn[region] = json.load(schema)
        log.debug("Loading cfn for : %s" % (region))
spec["cfn"] = cfn["us-east-1"]
log.info("Set global spec to us-east-1")
log.info("Assessing resource availability in regions [%s]" % (
    ",".join(cfn.keys())))

for resource in spec["cfn"]["PropertyTypes"].keys():
    log.debug("Processing Resource: %s" % (resource))
    spec["cfn"]["PropertyTypes"][resource]["RegionSupport"] = []
    for region in cfn.keys():
        if resource in cfn[region]["PropertyTypes"]:
            spec["cfn"]["PropertyTypes"][resource]["RegionSupport"].append(
                region)
            log.debug("\tAdding region: %s" % (region))


def massage_schema(schema):

    # Simplify Update Requires Data
    if isinstance(schema, dict):
        if 'UpdateRequires' in schema and '[' in schema["UpdateRequires"] and ']' in schema["UpdateRequires"]:
            schema["UpdateRequires"] = schema["UpdateRequires"].split(']')[
                0].split("[")[1]
            #    if 'no interruption' in schema['UpdateRequires']:
            # schema['UpdateRequires'] = "No interruption"
            #    elif 'replacement' in schema['UpdateRequires']:
            #        schema['UpdateRequires'] = "Replacement"

        # Set range as an example for AllowValues
        if 'Minimum' in schema and 'Maximum' in schema:
            if 'AllowedValues' not in schema:
                schema['AllowedValues'] = "%s...%s" % (
                    schema['Minimum'], schema['Maximum'])

        # Coerce to camel case
        if "Allowed Values" in schema and "AllowedValues" not in schema:
            schema["AllowedValues"] = schema["Allowed Values"]
            del schema["Allowed Values"]

        # Normalize Format
        if 'AllowedValues' in schema:
            if '|' in schema['AllowedValues']:
                schema['AllowedValues'] = schema['AllowedValues'].split('|')

            # isinstance(schema['AllowedValues'],dict)
            if isinstance(schema['AllowedValues'], list):
                schema['SampleValue'] = sorted(schema['AllowedValues'])[0]

            schema['CompliantValues'] = schema['AllowedValues']
        else:
            if 'Type' in schema and schema['Type'] in spec["PropertyTypes"]:
                schema['SampleValue'] = spec["PropertyTypes"][schema['Type']]

        # step into keys and massage as properties inbcase nested
        for k, v in schema.items():
            try:
                schema[k] = massage_schema(schema[k])
            except Exception as e:

                log.warning(e)
                log.warning(schema)

            if 'List of [' in v:
                schema[k] = [v.split('List of [')[1]]
    return schema


def expand_property(cfn_ref, property_name, data):
    cfn_ref = ""
    return


# Enumerate all Resource DOCs
for file in glob.glob("doc_source/AWS_*"):
    with open(file, 'r') as f:
        for line in f.readlines():
            if "+" in line:
                resource = line.split("]")[0].split('[')[1]
                key = resource.lower().replace('::', '-')
                # log.debug((resource, key))
                spec["Docs2Resource"][key] = resource


# Enumerate all resource Properties DOCs
for file in glob.glob('doc_source/aws-properties-*.json'):
    # log.debug(file)
    # e.g. aws-properties-amplify-branch-environmentvariable.md.properties.json

    """
    kinesisanalyticsv2.application.codecontent.s3contentlocation --> {'Required': 'No', 'Type': 'S3ContentLocation', 'UpdateRequires': '[No interruption](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-no-interrupt)'}
    kinesisanalyticsv2.application.codecontent.textcontent --> {'Minimum': '0', 'Required': 'No', 'Type': 'String', 'Maximum': '102400', 'UpdateRequires': '[No interruption](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-no-interrupt)'}
    """

    with open(file, 'r') as f:
        try:
            data = json.loads(f.read())
            if isinstance(data, dict):
                for key in data.keys():
                    docs_key = key.replace("aws-properties-", "").lower()
                    schema = massage_schema(data[key])
                    spec["PropertyTypes"][docs_key] = schema
                    log.debug("%s -->\n %s" %
                              (docs_key, json.dumps(schema, indent=4)))
            else:
                log.warning("data is not dict: \n %s" %
                            (json.dumps(data, indent=4)))
        except Exception as e:
            logging.exception(
                'Exception Enumerating all resource Properties DOCs')

types = {}
# Enumerate all resource Types
for file in sorted(glob.glob('doc_source/aws-resource-*.json')):
    # log.debug(file)
    with open(file, 'r') as f:

        try:
            data = json.loads(f.read())

            # extract single key for resource definition and value
            for key in data.keys():
                log.debug("\n------------------------\nKey: %s" % (key))
                try:
                    docs_key = 'aws-%s' % (key.replace("-properties", "")).lower()
                    if docs_key not in spec["Docs2Resource"]:
                        docs_key = 'aws-resource-%s' % (
                            key.replace("-properties", ""))

                    resource = spec["Docs2Resource"][docs_key]

                    spec["ResourceTypes"][resource] = data[key]

                    for k, v in data[key].items():
                        # "amazonmq-broker-configurationid-properties"
                        # log.debug(k)

                        docs_property_key = "%s-%s-properties" % (
                            resource.lower().replace("::", "-"), k.lower())
                        field_ref = resource + '.' + k

                        log.debug("docs_property_key [%s]" % (
                            docs_property_key))
                        log.debug("field_ref [%s]" % (field_ref))
                        log.debug("k [%s]" % (k))
                        log.debug("v [%s]" % (json.dumps(v, indent=4)))
                        # field_ref

                        if "Type" in v:
                            field_type = v["Type"].replace("#", "").strip()
                            item_type = "Literal"

                            if "List of " in field_type:
                                field_type = field_type.split('[')[1]
                                item_type = "List"

                            elif "Map of " in field_type:
                                field_type = field_type.split('[')[1]
                                item_type = "Map"

                            # append sample
                            spec["ResourceTypes"][field_ref] = data[key][k]
                            spec["ResourceTypes"][field_ref]["CloudResourceType"] = resource
                            spec["ResourceTypes"][field_ref]["CloudResourceProperty"] = k
                            spec["ResourceTypes"][field_ref]["CloudReference"] = field_ref
                            spec["ResourceTypes"][field_ref]["CloudResourceItemType"] = item_type
                            spec["ResourceTypes"][field_ref]["CloudExpectedValues"] = "TODO"

                            log.debug("I'm here")

                            for property_name in data[key][k].keys():
                                property_name = property_name.split('`')[0]
                                if property_name not in all_keys:
                                    all_keys.add(property_name)
                                    log.debug(
                                        "Adding all_keys [%s]" % (property_name))

                            property_key = "%s-%s-%s" % (
                                resource.lower(), key.lower(), field_type.lower())
                            # log.debug("property_key [%s]" % (property_key))
                            if len(field_type) > 0:
                                if field_type not in types:
                                    types[field_type] = []
                                propKey = key.replace(
                                    "-properties", "-%s-properties" % (field_type.lower()))
                                log.debug("propKey [%s]" % (propKey))
                                sample = ''
                                if propKey in spec["PropertyTypes"]:
                                    sample = spec["PropertyTypes"][propKey]
                                    spec["ResourceTypes"][field_ref]["CloudPropertySample"] = sample

                                types[field_type].append([propKey, sample])
                            # log.debug(json.dumps(v, indent=4))

                except Exception as e:
                    log.debug("Exception")
                    log.debug((file, key))
                    log.debug(e)
        except:
            logging.exception("Failed loading JSON: %s" % (file))
            log.warning(json.dumps(data, indent=4))

log.debug(json.dumps(types, indent=4))
log.debug(json.dumps(sorted(list(all_keys)), indent=4))


# process documentation nodes
rules = {
    "all": []
}
count_matched = 0

rules_graph = {
    "vertices": [],
    "edges": []
}

cfn_sample = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "CFNGuardGoat",
    "Metadata": {},
    "Parameters": {},
    "Rules": {},
    "Mappings": {},
    "Conditions": {},
    "Transform": {},
    "Resources": {},
    "Outputs": {}
}


def add_rule(resource, rule):
    comment = "# "
    resource_type = inflection.parameterize(resource)
    if resource_type not in rules.keys():
        log.info("Adding rules file for: %s - %s " % (resource_type, resource))
        rules[resource_type] = []

    rules['all'].append(comment + rule)
    rules[resource_type].append(comment + rule)

    # maintain vertices for each rule
    # ~id,~label,Documentation,hierarchy
    rule_id = inflection.parameterize(rule.split('<<')[0])

    if rule_id not in rules_graph["vertices"]:
        rules_graph["vertices"].append({
            "~id": "",
            "~label": "",
            "Documentation": "",
            "hierarchy": ""
        })
    else:
        log.info("Duplicate rule_id: %s" % rule_id)


def generate_sample_property(resource, property, type):
    property_key = "%s-"
    if type in spec["PropertyTypes"]:
        """
            "Boolean": "True",
            "Double": "123.45",
            "Float": "1.23456789",
        """
        return spec["PropertyTypes"][type]
    else:
        return {}


for resource in spec["cfn"]["ResourceTypes"]:
    resource_id = inflection.parameterize(resource)

    # create reference template
    cfn_sample["Resources"][resource_id] = {
        "Type:": resource,
        "Metadata": {},
        "Properties": {}
    }

    docs = spec["cfn"]["ResourceTypes"][resource]['Documentation']

    log.debug(docs)
    cfn_resource_json = "./doc_source/aws-%s.md.properties.json" % (
        docs.split("/aws-")[-1].split('.html')[0])
    matched = os.path.isfile(cfn_resource_json)
    log.debug('[%s] %s - %s' % (matched, resource, cfn_resource_json))
    if matched:
        with open(cfn_resource_json, 'r') as resource_json:
            # contents = resource_json.read()
            data = json.load(resource_json)
            log.debug(json.dumps(data))
            for property in spec["cfn"]["ResourceTypes"][resource]["Properties"]:

                cfn_sample["Resources"][resource_id]["Properties"][property] = ""

                cfn_guard_selector = "%s %s" % (resource, property)
                cfn_docs_selector = (
                    "%s-%s" % (resource.lower().replace('::', '.'), property)).lower()
                docs = spec["cfn"]["ResourceTypes"][resource]["Properties"][property]['Documentation']
                cfn_doc_id = docs.split('#')[-1]
                cfn_prefix = cfn_doc_id.split("-")[0]
                cfn_doc_id = cfn_doc_id[len(cfn_prefix)+1:]
                log.debug("Property: %s %s " % (resource, property))
                for key in data.keys():

                    if key.split('.')[-1].lower() == property.lower():
                        log.debug("Property: %s %s " % (resource, property))
                        log.debug(json.dumps(data[key], indent=4))
                        spec['cfn']['ResourceTypes'][resource]["Properties"][property].update(
                            data)  # merge dict keys into global model

                        try:
                            # start pruning the noise now
                            del data[key]["UpdateRequires"]
                        except:
                            pass

                        if property.lower()[-4:] == "name" or property.lower()[-11:] == "description":
                            if "Minimum" in data[key] and "Maximum" in data[key]:

                                add_rule(
                                    resource,
                                    "%s %s  == /\S{%s,%s}/ <<  %s is a required property for %s" % (
                                        resource,
                                        property,
                                        data[key]["Minimum"],
                                        data[key]["Maximum"],
                                        property,
                                        resource
                                    )
                                )
                                del data[key]["Minimum"]  # prune
                                del data[key]["Maximum"]  # prune

                            elif "Maximum" in data[key]:
                                add_rule(
                                    resource,
                                    "%s %s  == /arn.*{0,%s}/ <<  %s is a required property for %s" % (
                                        resource,
                                        property,
                                        data[key]["Maximum"],
                                        property,
                                        resource
                                    )
                                )
                                del data[key]["Maximum"]  # prune

                        if property.lower()[-3:] == "arn":
                            if "Minimum" in data[key] and "Maximum" in data[key]:

                                add_rule(
                                    resource,
                                    "%s %s  == /arn.*{%s,%s}/ <<  %s is a required property for %s" % (
                                        resource,
                                        property,
                                        data[key]["Minimum"],
                                        data[key]["Maximum"],
                                        property,
                                        resource
                                    )
                                )
                                del data[key]["Minimum"]  # prune
                                del data[key]["Maximum"]  # prune
                            elif "Maximum" in data[key]:

                                add_rule(
                                    resource,
                                    "%s %s  == /arn.*{0,%s}/ <<  %s is a required property for %s" % (
                                        resource,
                                        property,
                                        data[key]["Maximum"],
                                        property,
                                        resource
                                    )
                                )
                                del data[key]["Maximum"]  # prune

                        if "Required" in data[key] and data[key]['Required'] == 'Yes':

                            add_rule(
                                resource,
                                "%s %s  == /.*/ <<  %s is a required property for %s" %
                                (resource, property, property, resource)
                            )
                            del data[key]["Required"]  # prune

                        if "Pattern" in data[key]:

                            add_rule(
                                resource,
                                "%s %s  == /%s/ <<  %s is a required pattern for %s" % (
                                    resource,
                                    property,
                                    data[key]["Pattern"],
                                    property,
                                    resource
                                )
                            )

                            if "Minimum" in data[key]:
                                del data[key]["Minimum"]

                            if "Maximum" in data[key]:
                                del data[key]["Maximum"]

                            del data[key]["Pattern"]  # prune

                        if "Type" in data[key]:

                            if data[key]["Type"] == "List of [Tag":
                                # prune - pick up with * Tag wildcard rule
                                del data[key]["Type"]

                            elif data[key]["Type"] == "Boolean":
                                add_rule(
                                    resource,
                                    "%s %s  == True <<  True is expected safe default value" % (
                                        resource,
                                        property
                                    )
                                )

                                add_rule(
                                    resource,
                                    "%s %s  == False <<  False is expected  safe default value" % (
                                        resource,
                                        property
                                    )
                                )

                                del data[key]["Type"]  # prune

                            elif data[key]["Type"] == "Integer":
                                # TODO : validate regex logic
                                add_rule(
                                    resource,
                                    "%s %s  == /[0-9].+/ <<  Integer is expected for %s of %s " % (
                                        resource,
                                        property,
                                        resource,
                                        property
                                    )
                                )

                                if "Minimum" in data[key]:
                                    add_rule(
                                        resource,
                                        "%s %s  >= %s <<  Integer is expected for %s of %s " % (
                                            resource,
                                            property,
                                            data[key]["Minimum"],
                                            resource,
                                            property
                                        )
                                    )

                                    del data[key]["Minimum"]  # prune

                                if "Maximum" in data[key]:
                                    add_rule(resource,
                                             "%s %s  <= %s <<  Integer is expected for %s of %s " % (
                                                 resource,
                                                 property,
                                                 data[key]["Maximum"],
                                                 resource,
                                                 property
                                             )
                                             )
                                    del data[key]["Maximum"]  # prune

                                del data[key]["Type"]

                        if "AllowedValues" in data[key]:
                            data[key]["Allowed values"] = ' | '.join(
                                data[key]["AllowedValues"])
                            del data[key]["AllowedValues"]

                        if "Allowed values" in data[key]:
                            allowed = []
                            allowed_options = data[key]["Allowed values"].split(
                                ' | ')

                            add_rule(
                                resource,
                                "%s %s IN [%s] << Enforcing Allowed Values only" % (
                                    resource,
                                    property,
                                    ",".join(allowed_options))
                            )

                            for allowed_value in allowed_options:
                                # AWS::EC2::Volume AvailabilityZone == us-west-2b |OR| AWS::EC2::Volume AvailabilityZone == us-west-2c
                                allowed.append("%s %s  == %s" % (
                                    resource, property, allowed_value))

                                add_rule(
                                    resource,
                                    "%s %s  == /%s/ <<  %s is an expected value for %s %s" % (
                                        resource,
                                        property,
                                        allowed_value,
                                        allowed_value,
                                        resource,
                                        property
                                    )
                                )

                            message = " << Enforce allowed values [%s]" % (
                                ' | '.join(allowed_options))

                            add_rule(
                                resource,
                                '#' + ' |OR| '.join(allowed) + message
                            )
                            del data[key]["Allowed values"]

                        if "Type" in data[key] and data[key]["Type"] == "String":
                            if "Minimum" not in data[key] and "Maximum" in data[key]:
                                # TODO: validate regex pattern

                                add_rule(
                                    resource,
                                    "%s %s  == /\S{0,%s}/ <<  %s is an expected length of String property for %s" % (
                                        resource,
                                        property,
                                        data[key]["Maximum"],
                                        resource,
                                        property
                                    )
                                )
                                # del data[key]["Minimum"]
                                del data[key]["Maximum"]
                            if "Minimum" in data[key] and "Maximum" in data[key]:
                                # TODO: validate regex pattern

                                add_rule(
                                    resource,
                                    "%s %s  == /\S{%s,%s}/ <<  %s is an expected length of String property for %s" % (
                                        resource, property, data[key]["Minimum"], data[key]["Maximum"], resource, property)
                                )
                                del data[key]["Minimum"]
                                del data[key]["Maximum"]
                            del data[key]["Type"]
                        try:
                            del data[key]["Required"]
                        except:
                            pass

                        if "Type" in data[key] and property != "Tags":
                            if data[key]["Type"] == "List of String":
                                log.info(
                                    "Not implemented - data[key][\"Type\"] == \"List of String\" ")
                                del data[key]["Type"]

                            data_type = "%s.%s" % (
                                resource, property)  # data[key]["Type"]
                            known_type = data_type in spec["cfn"]["PropertyTypes"]
                            singular_type = data_type[:-
                                                      1] in spec["cfn"]["PropertyTypes"]
                            if singular_type:
                                data_type = data_type[: -1]
                                known_type = True

                            if known_type:
                                log.debug("Known Data Type: %s [%s]" % (
                                    data_type, known_type))
                                if "Properties" in spec["cfn"]["PropertyTypes"][data_type]:
                                    sub_properties = spec["cfn"]["PropertyTypes"][data_type]["Properties"]
                                    for sub_property in sub_properties:
                                        sub_selector = "%s %s.%s" % (
                                            resource, property, sub_property.split('.')[-1])
                                        wilcard_selector = "* %s.%s" % (
                                            property, sub_property.split('.')[-1])

                                        # log.warning("Property: %s" % (sub_property))
                                        try:
                                            del sub_properties[sub_property]["Documentation"]
                                        except:
                                            pass  # not the droids
                                        try:
                                            del sub_properties[sub_property]["UpdateType"]
                                        except:
                                            pass  # not the droids

                                        if "PrimitiveType" in sub_properties[sub_property]:
                                            if sub_properties[sub_property]["PrimitiveType"] == "String":
                                                if sub_properties[sub_property]["Required"] == "True":
                                                    add_rule(
                                                        resource,
                                                        "%s  == /\S/ <<  %s is a required String property for %s" % (
                                                            sub_selector, resource, property)
                                                    )
                                                    # rules['todo'].append(
                                                    #    "%s  == /\S/ <<  %s is a required String property for all resources" % (wilcard_selector, property))
                                                else:
                                                    add_rule(
                                                        resource,
                                                        "%s  == /\S/ <<  %s is an expected but optional String property for %s" % (
                                                            sub_selector, resource, property)
                                                    )
                                                    # rules['todo'].append(
                                                    #    "%s  == /\S/ <<  %s is an expected but optional String property for all resources" % (wilcard_selector, property))
                                            del sub_properties[sub_property]["PrimitiveType"]
                                            del sub_properties[sub_property]["Required"]

                                        if "Type" in sub_properties[sub_property]:
                                            if sub_properties[sub_property]["Type"] == "Integer":

                                                add_rule(
                                                    resource,
                                                    "%s  == /[0-9].+/ <<  %s must be an expected but an Integer property for %s" % (
                                                        sub_selector, resource, property)
                                                )
                                                del sub_properties[sub_property]["Type"]

                                        # waf-bytematchset-bytematchtuples-fieldtomatch
                                        coerced_file_part = "%s-%s" % (
                                            resource, property)
                                        coerced_file_part = coerced_file_part.lower().replace(
                                            "::", "-").replace(" ", "-").replace("wafv2", "waf")[4:]
                                        sub_selector_doc_file = "./doc_source/aws-properties-%s.md.properties.json" % (
                                            coerced_file_part)
                                        file_found = os.path.isfile(
                                            sub_selector_doc_file)
                                        # show the trailing unhandled properties
                                        if file_found:
                                            with open(sub_selector_doc_file, 'r') as props_file:
                                                sub_props = json.load(
                                                    props_file)
                                                # log.info(json.dumps(sub_props))

                                                for ignore_property in ['UpdateRequires', 'Documentation', 'Update Requires', 'UpdateRequires']:
                                                    try:
                                                        del sub_props[ignore_property]
                                                    except:
                                                        pass

                                                for prop_key, prop_value in sub_props.items():
                                                    drill_in_selector = "%s.%s" % (
                                                        property, prop_key.split('.')[-1])
                                                    log.info(drill_in_selector)
                                                    log.info(json.dumps(
                                                        sub_props[prop_key], indent=4))

                                                    if "AllowedValues" in sub_props[prop_key]:
                                                        sub_props[prop_key]["Allowed values"] = sub_props[prop_key]["AllowedValues"]
                                                        del sub_props[prop_key]["AllowedValues"]

                                                    if "Allowed values" in sub_props[prop_key]:
                                                        try:
                                                            allowed_values = sub_props[prop_key]["Allowed values"].split(
                                                                " | ")
                                                        except:
                                                            allowed_values = sub_props[prop_key]["Allowed values"]

                                                        add_rule(
                                                            resource,
                                                            "%s IN [%s] << Enforce Allowed Values" % (
                                                                drill_in_selector, ','.join(allowed_values))
                                                        )

                                                        for value in allowed_values:

                                                            add_rule(
                                                                resource,
                                                                "%s == %s << Enforce Expected Value for %s" % (
                                                                    drill_in_selector, value, prop_key)
                                                            )
                                                        del sub_props[prop_key]["Allowed values"]

                                                    if "Required" in sub_props[prop_key]:
                                                        if sub_props[prop_key]['Required'] == 'Yes':

                                                            add_rule(
                                                                resource,
                                                                "%s %s.%s  == /.*/ <<  %s is a required property for %s %s" % (
                                                                    resource, property, prop_key, prop_key, resource, property)
                                                            )

                                                        elif sub_props[prop_key]['Required'] == 'Conditional':

                                                            add_rule(
                                                                resource,
                                                                "%s %s.%s  == /.*/ <<  %s is a Conditional property for %s %s" % (
                                                                    resource, property, prop_key, prop_key, resource, property)
                                                            )
                                                        # prune
                                                        del sub_props[prop_key]["Required"]

                                                    if "Pattern" in data[key]:

                                                        add_rule(
                                                            resource,
                                                            "%s %s  == /%s/ <<  %s is a required pattern for %s" % (
                                                                resource, property, data[key]["Pattern"], property, resource)
                                                        )

                                                        if "Minimum" in data[key]:
                                                            del data[key]["Minimum"]

                                                        if "Maximum" in data[key]:
                                                            del data[key]["Maximum"]

                                        elif sub_properties[sub_property].keys():
                                            log.info(
                                                "Selector: %s [%s - %s]" % (sub_selector, sub_selector_doc_file, file_found))
                                            log.info(json.dumps(
                                                sub_properties[sub_property], indent=4))
                            else:

                                log.warning("Unknown Data Type: %s [%s]" % (
                                    data_type, known_type))
                                log.warning(json.dumps(data[key], indent=4))

                        if len(data[key].keys()) > 1000:
                            log.info("%s %s" % (resource, property))
                            log.info(json.dumps(data[key], indent=4))

                if matched:
                    count_matched += 1
                # [cfn] aws.cognito.userpoolidentityprovider-attributemapping --> AWS::Cognito::UserPoolIdentityProvider AttributeMapping [cognito-userpoolidentityprovider-attributemapping]
                log.debug("[%s] %s --> %s [%s]" % (cfn_prefix,
                          cfn_docs_selector, cfn_guard_selector, cfn_doc_id))
    else:
        log.warning("Unmatched resource: %s" % (resource))


for property_type, properties in spec["cfn"]["PropertyTypes"].items():
    log.debug("Property Type: %s" % (property_type))
    selector = "* %s"


with open("rulesets/all.rules.txt", 'w') as f:
    f.write('\n'.join(sorted(list(set(rules['all'])))))
    log.warning("Written %s rules" % (len(rules)))

for key in rules.keys():
    if key != "all":
        with open("rulesets/%s.rules.txt" % (key), 'w') as f:
            f.write('\n'.join(sorted(list(set(rules[key])))))
            log.warning("Written %s [%s] rules" % (key, len(rules[key])))

log.warning("Matched :%s" % (count_matched))

with open("spec.json", 'w') as f:
    f.write(json.dumps(spec, indent=4, sort_keys=True))
    log.warning("Written spec.json")

with open("cfn_sample.json", 'w') as f:
    f.write(json.dumps(cfn_sample, indent=4, sort_keys=True))
    log.warning("Written cfn_sample.json")
