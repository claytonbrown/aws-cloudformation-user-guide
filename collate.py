import glob
import json
import csv
import os
import logging

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
        worker = kinesishandler.Worker(q, "aws-account-base-stream", region="us-east-1")
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
setup_logging(log, verbosity=logging.WARNING)



f = csv.writer(open("test.csv", "w", newline=''))
f.writerow(["resource", "model", "codename", "name", "content_type"])

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

all_keys = set()

def massage_schema(schema):

    # Simplify Update Requires Data
    if isinstance(schema, dict):
        if 'UpdateRequires' in schema and '[' in schema["UpdateRequires"] and ']' in schema["UpdateRequires"]:
            schema["UpdateRequires"] = schema["UpdateRequires"].split(']')[0].split("[")[1]
            #    if 'no interruption' in schema['UpdateRequires'].lower():
            ##        schema['UpdateRequires'] = "No interruption"
            #    elif 'replacement' in schema['UpdateRequires'].lower():
            #        schema['UpdateRequires'] = "Replacement"

        # Set range as an example for AllowValues
        if 'Minimum' in schema and 'Maximum' in schema:
            if 'AllowedValues' not in schema:
                schema['AllowedValues'] = "%s...%s" % (schema['Minimum'],schema['Maximum'])

        # Coerce to camel case
        if "Allowed Values" in schema and "AllowedValues" not in schema:
            schema["AllowedValues"] = schema["Allowed Values"]
            del schema["Allowed Values"]

        # Normalize Format
        if 'AllowedValues' in schema:
            if '|' in schema['AllowedValues']:
                schema['AllowedValues'] = schema['AllowedValues'].split('|')


            if isinstance(schema['AllowedValues'],list): #  isinstance(schema['AllowedValues'],dict)
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
                schema[k] = [ v.split('List of [')[1] ]
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
                    docs_key = key.replace("aws-properties-", "")
                    schema = massage_schema(data[key])
                    spec["PropertyTypes"][docs_key] = schema
                    log.info("%s -->\n %s" % (docs_key, json.dumps(schema, indent=4)))
            else:
                log.warn("data is not dict: \n %s" % (json.dumps(data, indent=4)))
        except Exception as e:
            logging.exception('Exception Enumerating all resource Properties DOCs')

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
                    docs_key = 'aws-%s' % (key.replace("-properties", ""))
                    if docs_key not in spec["Docs2Resource"]:
                        docs_key = 'aws-resource-%s' % (key.replace("-properties", ""))

                    resource = spec["Docs2Resource"][docs_key]

                    spec["ResourceTypes"][resource] = data[key]

                    for k, v in data[key].items():
                        # "amazonmq-broker-configurationid-properties"
                        # log.debug(k)

                        docs_property_key = "%s-%s-properties" % (resource.lower().replace("::", "-"), k.lower())
                        field_ref = resource + '.' + k

                        log.debug("docs_property_key [%s]" % (docs_property_key))
                        log.debug("field_ref [%s]" % (field_ref))
                        log.debug("k [%s]" % (k))
                        log.debug("v [%s]" % (json.dumps(v, indent=4)))
                        #field_ref

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
                                    log.debug("Adding all_keys [%s]" % (property_name))

                            property_key = "%s-%s-%s" % (resource, key, field_type.lower())
                            # log.debug("property_key [%s]" % (property_key))
                            if len(field_type) > 0:
                                if field_type not in types:
                                    types[field_type] = []
                                propKey = key.replace("-properties", "-%s-properties" % (field_type.lower()))
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
            log.warning(json.dumps(data,indent=4))

log.debug(json.dumps(types, indent=4))
log.debug(json.dumps(sorted(list(all_keys)), indent=4))

with open("spec.json", 'w') as f:
    f.write(json.dumps(spec, indent=4))
    log.debug("written json")
