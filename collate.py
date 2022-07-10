import glob
import json
import csv
import os
import logging
import sys
import inflection
from botocore.session import get_session
from colorlog import ColoredFormatter



log = logging.getLogger()
verbosity = logging.INFO
logging.basicConfig(filename='debug.log', level=verbosity)
formatter_console_colour = "%(log_color)s%(levelname)-8s %(module)s:%(lineno)d- %(name)s%(reset)s %(blue)s%(message)s"
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(verbosity)
console_handler.setFormatter(ColoredFormatter(
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
))
log.addHandler(console_handler)
log.info("logging initialized")


log = logging.getLogger()


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

for file in glob.glob("aws-cfn-resource-specs/specs/*/CloudFormationResourceSpecification.json"):
    log.debug("Processing CFN Spec: %s" %(file))
    region = file.rstrip('.json').split('aws-cfn-resource-specs/specs/')[1].split('/')[0].lower().strip()
    log.debug(region)
    with open(file, 'r') as schema:
        cfn[region] = json.load(schema)
        log.info("Loading cfn for : %s" % (region))

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

# collate doc_source property information from aws_cloudformation_docs which includes allowed values, min/max, property descriptions etc
for file in glob.glob('doc_source/*.json'):
    log.debug("Ingesting documentation: %s" % (file))
    with open(file, 'r') as doc_source:
        try:
            doc_data = json.loads(doc_source.read())
            # log.debug(json.dumps(doc_data, indent=4))
            for k, v in doc_data.items():
                if k in spec["cfn"]["PropertyTypes"]:
                    # merge dicts
                    spec["cfn"]["PropertyTypes"][k].update(v)
                    log.info("Merged: %s" % (k))
                else:
                    # create new key value
                    spec["cfn"]["PropertyTypes"][k] = v
                    log.debug("Added Doc Source: %s" % (k))
                    log.debug(json.dumps(v,indent=4))

        except Exception as e:
            log.warning(e)


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
                spec["Docs2Resource"][key.replace('-','.')] = resource
                spec["Docs2Resource"][key.replace('-','.').replace('aws.','')] = resource


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
    "v1":{
        "all": []
    },
    "v2":{
        "all": []
    }
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


def add_rule(resource, rule, v2rule=None):
    comment = "# "
    resource_type = inflection.parameterize(resource)
    if resource_type not in rules['v1'].keys():
        log.debug("Adding v1 rules file for: %s - %s " % (resource_type, resource))
        rules['v1'][resource_type] = []

    if resource_type not in rules['v2'].keys():
        log.debug("Adding v2 rules file for: %s - %s " % (resource_type, resource))
        rules['v2'][resource_type] = []

    rules['v1']['all'].append(comment + rule)
    rules['v1'][resource_type].append(comment + rule)

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

docs2_resource = {}

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

                #property_key = resource.lower().replace("::",'-')
                #doc_source_resource_filename = ("doc_source/aws-resource-%s.md.properties.json" % (property_key)).replace('-resource-aws-','-resource-')
                #if os.path.isfile(doc_source_resource_filename):
                #    try:
                #        with open(doc_source_resource_filename) as doc_file:
                #            doc_data = json.loads(doc_file.read())
                #            for key, value in doc_data.items()



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
                                #property_key = resource.lower().replace("::",'-')
                                #doc_source_resource_filename = ("doc_source/aws-resource-%s.md.properties.json" % (property_key)).replace('-resource-aws-','-resource-')
                                #if os.path.isfile(doc_source_resource_filename):
                                #    with open(doc_source_resource_filename) as doc_file:
                                #        doc_data = json.loads(doc_file.read())
                                # log.info("DocSource [%s] %s" % (doc_source_exists, doc_source_resource_filename))
                                log.info("Not implemented - data[%s][\"Type\"] == \"List of String\" " % (key))

                                del data[key]["Type"]



                            data_type = "%s.%s" % (
                                resource, property)  # data[key]["Type"]
                            known_type = data_type in spec["cfn"]["PropertyTypes"]
                            singular_type = data_type[:-1] in spec["cfn"]["PropertyTypes"]

                            # AWS::DAX::SubnetGroup.SubnetIds | aws-resource-dax-subnetgroup.md.properties.json
                            # TOD

                            if singular_type:
                                data_type = data_type[: -1]
                                known_type = True

                            if known_type:
                                log.debug("Known Data Type: %s [%s]" % (
                                    data_type, known_type))
                                if "Properties" in spec["cfn"]["PropertyTypes"][data_type]:
                                    sub_properties = spec["cfn"]["PropertyTypes"][data_type]["Properties"]
                                    for sub_property in sub_properties:
                                        sub_selector = "%s %s.%s" % (resource, property, sub_property.split('.')[-1])
                                        doc_selector = "%s.%s.%s" % (
                                                resource.lstrip("AWS::").lower().replace("::","."),
                                                property.lower(),
                                                sub_property.split('.')[-1]
                                        )
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
                                                    log.debug(drill_in_selector)
                                                    log.debug(json.dumps(
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
                                            log.info("Selector: %s [%s - %s]" % (doc_selector, sub_selector_doc_file, file_found))
                                            log.info(json.dumps(sub_properties[sub_property], indent=4))
                                            if doc_selector in spec["cfn"]["PropertyTypes"]:
                                                log.info(json.dumps(spec["cfn"]["PropertyTypes"][doc_selector], indent=4))
                                            else:
                                                log.warning("Could not locate doc_selector: %s" % (doc_selector))
                                            """
                                            Selector: AWS::S3::Bucket MetricsConfigurations.TagFilters [./doc_source/aws-properties-s3-bucket-metricsconfigurations.md.properties.json - False]
                                            INFO     collate:833- root {
                                                "DuplicatesAllowed": false,
                                                "ItemType": "TagFilter",
                                                "Required": false,
                                                "Type": "List"
                                            }
                                            cat ./doc_source/aws-properties-s3-bucket-metricsconfigurations.md.properties.json
                                            cat ./doc_source/aws-properties-s3-bucket-metricsconfiguration.md.properties.json | jq .
                                            {
                                              ...
                                              "s3.bucket.metricsconfiguration.TagFilters": {
                                                "Docs": "Specifies a list of tag filters to use as a metrics configuration filter. The metrics configuration includes only objects that meet the filter's criteria.",
                                                "Required": "No",
                                                "Type": "List of [TagFilter",
                                                "UpdateRequires": "[No interruption](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-no-interrupt)\n\n#"
                                              }
                                            }
                                            """
                            else:
                                # Unknown Data Type: AWS::S3::BucketPolicy.PolicyDocument [False]
                                #  cat doc_source/aws-properties-s3-bucket-inventoryconfiguration.md.properties.json | jq .
                                # "s3.bucket.inventoryconfiguration.Destination"
                                # ls ./doc_source/aws-properties-s3-bucket-metricsconfiguration.md.properties.json
                                # AWS::Lightsail::Distribution.CacheBehaviorSettings

                                log.warning("Unknown Data Type: %s [%s]" % (data_type, known_type))
                                try:
                                    log.info(json.dumps(spec["cfn"]["PropertyTypes"][doc_selector], indent=4))
                                except:
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


for property_type, data in spec["cfn"]["PropertyTypes"].items():
    log.debug("Property Type: %s" % (property_type))
    selector = "* %s"

    """
        "cfn": {
        "PropertyTypes": {
             "AWS::ACMPCA::Certificate.EdiPartyName": {
                "Documentation": "http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-acmpca-certificate-edipartyname.html",
                "Properties": {
                    "NameAssigner": {
                        "Documentation": "http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-acmpca-certificate-edipartyname.html#cfn-acmpca-certificate-edipartyname-nameassigner",
                        "PrimitiveType": "String",
                        "Required": true,
                        "UpdateType": "Immutable"
                    },
                    "PartyName": {
                        "Documentation": "http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-acmpca-certificate-edipartyname.html#cfn-acmpca-certificate-edipartyname-partyname",
                        "PrimitiveType": "String",
                        "Required": true,
                        "UpdateType": "Immutable"
                    }
                },
                "RegionSupport": ["
    """
    if not "Properties" in data:
        log.warning("PropertyType has not properties: %s" % (property_type))
        log.info(json.dumps(data, indent=4))
    else:
        try:
            resource_name, property_name = property_type.split('.')
            for sub_property in data["Properties"]:
                property_docs_index = "%s-%s-%s" % (resource_name, property_name, sub_property).lower().replace('::','-')
                log.warning("DocsKey: %s" % (property_docs_index))
        except Exception as e:
            log.warning(e)



with open("rulesets/v1/all.rules.txt", 'w') as f:
    f.write('\n'.join(sorted(list(set(rules['v1']['all'])))))
    log.info("Written %s rules" % (len(rules['v1'])))

for key in rules['v1'].keys():
    if key != "all":
        dest_file = "rulesets/v1/%s.rules.txt" % (key)
        with open(dest_file, 'w') as f:
            f.write('\n'.join(sorted(list(set(rules['v1'][key])))))
            log.debug("Written %s [%s] rules" % (dest_file, len(rules['v1'][key])))
log.info("Written v1 rulesets")

for key in rules['v2'].keys():
    if key != "all":
        dest_file = "rulesets/v2/%s.rules.txt" % (key)
        with open(dest_file, 'w') as f:
            f.write('\n'.join(sorted(list(set(rules['v2'][key])))))
            log.debug("Written %s [%s] rules" % (dest_file, len(rules['v2'][key])))
log.info("Written v2 rulesets")

log.warning("Matched :%s" % (count_matched))

with open("spec.json", 'w') as f:
    f.write(json.dumps(spec, indent=4, sort_keys=True))
    log.info("Written spec.json")

with open("cfn_sample.json", 'w') as f:
    f.write(json.dumps(cfn_sample, indent=4, sort_keys=True))
    log.info("Written cfn_sample.json")
