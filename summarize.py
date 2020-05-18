import json
import logging
from colorlog import ColoredFormatter
import glob
import sys

log = logging.getLogger()
verbosity = logging.INFO
logging.basicConfig(filename='debug.log', level=verbosity)
formatter_console_colour = "%(log_color)s%(levelname)-8s %(module)s:%(lineno)d- %(name)s%(reset)s %(blue)s%(message)s"
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

# aws-properties-autoscalingplans-scalingplan-scalinginstruction.md:*Allowed Values*: `KeepExternalPolicies | ReplaceExternalPolicies`
properties = {}
"""
input_file = "summary.txt"
with open(input_file, "r") as file:
    for line in file.readlines():
        try:
            key, value = line.replace("`", "").split('.md:*Allowed Values*: ')
            key = key.replace("aws-resource-", "")
            key = key.replace("aws-properties-", "")
            key = key.replace("-", ".")
            properties[key] = value.replace('\n', '').strip().split(' | ')

        except Exception as e:
            # log.debug(line)
            # log.debug(e)
            logging.debug(e)
            pass

    # work with exceptions
    properties["glue.job.jobcommand.pythonversion"] = ["2", "3"]
    properties["appsync.graphqlapi.authenticationtype"] = ["API_KEY", "AWS_IAM", "AMAZON_COGNITO_USER_POOLS", "OPENID_CONNECT"]
"""

cfn_schema = json.load(open('CloudFormationResourceSpecification.json','r'))
schema_key = {}
for resource_name, resource_properties in cfn_schema["ResourceTypes"].items():
    key = resource_name.lower().replace('::','.')
    schema_key[key] = resource_name
    log.info("%s --> %s" % (key, resource_name))

    if "Properties" in resource_properties:
        for resource_property_name, resource_property_detail in resource_properties["Properties"].items():
            property_key = "%s.%s" % (key, resource_property_name.lower())
            property_ref = "%s.%s" % (resource_name, resource_property_name)
            schema_key[property_key] = property_ref
            log.info("%s --> %s" % (property_key, property_ref))

files = glob.glob('doc_source/aws-properties-*.md.properties.json')
for file in files:

    log.debug(file)
    data = json.load(open(file,'r'))
    for k, v in data.items():

        if k in schema_key:
            v["Schema"] = schema_key[k]
            v["Service"] = schema_key[k].split('.')[0]

        # "UpdateRequires": "[No interruption](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-no-interrupt)"
        if "UpdateRequires" in v:
            if "no interruption" in v["UpdateRequires"].lower():
                v["UpdateRequires"] = "No interruption"
            else:
                v["UpdateRequires"] = "Replacement"

        if isinstance(v, dict):
            v["UniqueKey"] = k

            if len(v.keys()) == 3:
                v["SampleValue"] = 'TODO-' + k.split('.')[-1]

            # enforce regex for string length when no pattern provided
            if "Type" in v and v["Type"] == "String":
                if "Pattern" not in v and "Minimum" in v and "Maximum" in v:
                    template = "^.{%s,%s}$"
                    constrainedString = template % (int(v["Minimum"]), int(v["Maximum"]))
                    v["Pattern"] = constrainedString
                    v["SampleValue"] = "TODO-%s" % (k)
                    log.debug(constrainedString)

            # enforce regex for integer when no pattern provided
            if "Type" in v and v["Type"] == "Integer":
                if "Pattern" not in v and "Minimum" in v and "Maximum" in v:
                    template = "^[%s,%s]}$"
                    constrainedString = template % (int(v["Minimum"]), int(v["Maximum"]))
                    v["Pattern"] = constrainedString
                    v["SampleValue"] = "%s...%s" % (int(v["Minimum"]), int(v["Maximum"]))
                    log.debug(constrainedString)

            if "AllowedValues" in v and "SampleValue" not in v:
                # v["SampleValue"] = sorted(v["AllowedValues"])[0]
                v["SampleValue"] = "|".join(v["AllowedValues"])
                if "Pattern" not in v:
                    v["Pattern"] = "^[%s]" % (v["SampleValue"])
        else:
            log.warn(k)
            log.warn(json.dumps(v, indent=4))

        if "aws-properties-" in k:
            k = k.replace("aws-properties-","").replace("-properties","-cfnproperties").replace('-','.')
            v = list(v.keys())
            properties[k] = v
        else:

            properties[k] = v

log.info("%s properties files processed" % (len(files)))

log.debug(json.dumps(properties, indent=4))

output_file = 'allowed_values.json'
with open(output_file, 'w') as file:
    file.write(json.dumps(properties, indent=4, sort_keys=True))
    file.close()
    log.info("Written: %s" % (output_file))
