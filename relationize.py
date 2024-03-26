import json
import logging
from colorlog import ColoredFormatter
import glob
import sys
import os
import chevron
import exrex

from cog.torque import Graph
g = Graph("cfn")
# TODO: g.load_csv('test/test-data/books.csv', "book_id")


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

sample_rule = """
let resources = Resources.*[ Type == {{ resource_type }} ]
let allowed_values = [{{ allowed_values }}]

rule s3_buckets_allowed_sse_algorithm when %s3_buckets !empty {
    let encryption = %s3_buckets.Properties.BucketEncryption
    %{{ property_name }} exists
    %{{ matcher_rule}} in %allowed_values

}
"""
resource_rules = {}

cfn_selectors = {}

def add_rule(
        cfn_resource = 'AWS::S3::Bucket',
        cfn_property = 'encryption',
        path_match='encryption.ServerSideEncryptionConfiguration[*].ServerSideEncryptionByDefault.SSEAlgorithm',
        allowed_values_string=""
        ):

    if resource_rules not in resource_rules:
        resource_rules[cfn_resource] = []

    rule_sample = chevron.render(
            {
                'resource_type': cfn_resource,                  # e.g. 'AWS::S3::Bucket'
                'parent_property_name': cfn_property,           # e.g. %encryption exists
                'matcher_rule': path_match,                     # e.g. %encryption.ServerSideEncryptionConfiguration[*].ServerSideEncryptionByDefault.SSEAlgorithm
                'allowed_values': allowed_values_string         # e.g.
            }
    )
    log.info(rule_sample)
    resource_rules[cfn_resource].append(rule_sample)

sampleString = "abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 500

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
    key = resource_name #.replace('::','.')
    schema_key[key] = resource_name
    log.info("%s --> %s" % (key, resource_name))

    g.put("cfn","Resource",resource_name)


    # create CNF guard 2 resource selector
    cfn_selectors[resource_name] = {}

    if "Properties" in resource_properties:
        for resource_property_name, resource_property_detail in resource_properties["Properties"].items():
            property_key = "%s.%s" % (key, resource_property_name)
            property_ref = "%s.%s" % (resource_name, resource_property_name)
            schema_key[property_key] = property_ref
            log.info("%s --> %s" % (property_key, property_ref))

            cfn_selectors[resource_name][resource_property_name]= {}

            g.put(resource_name,"resource",resource_property_name)

files = glob.glob('doc_source/aws-properties-*.md.properties.json')
for file in files:

    log.debug(file)
    data = json.load(open(file,'r'))
    for k, v in data.items():
        try:


            # coerce two word key to camelcase Key AllowedValues
            if "Allowed values" in v:
                v["AllowedValues"] = v["Allowed values"]
                del v["Allowed values"]


            if k in schema_key:
                v["Schema"] = schema_key[k]
                v["Service"] = schema_key[k].split('.')[0]

            # "UpdateRequires": "[No interruption](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-no-interrupt)"
            if "UpdateRequires" in v:
                if "no interruption" in v["UpdateRequires"]:
                    v["UpdateRequires"] = "No interruption"
                else:
                    v["UpdateRequires"] = "Replacement"

            if isinstance(v, dict):
                v["UniqueKey"] = k.lower()

                if len(v.keys()) == 3:
                    v["SampleValue"] = 'TODO-' + k.split('.')[-1]

                # generate sample value from pattern
                if "Pattern" in v:
                    regexPattern = v["Pattern"] #.strip().replace('\n','').replace('\t','').replace('\r','').replace("\r\n\t","")
                    log.info("Pattern: %s " % (regexPattern ))
                    v["GeneratedSample"] = "TODO - fix encoding issue" # exrex.getone( regexPattern )
                    log.info("GeneratedSample %s --> %s" % (regexPattern, v["GeneratedSample"]))

                # enforce regex for string length when no pattern provided
                if "Type" in v and v["Type"] == "String":
                    if "Pattern" not in v and "Minimum" in v and "Maximum" in v:
                        template = "^.{%s,%s}$"
                        constrainedString = template % (int(v["Minimum"]), int(v["Maximum"]))
                        v["Pattern"] = constrainedString
                        v["SampleValue"] = "TODO-%s" % (k)
                        log.debug(constrainedString)

                    # generate sample string of string length
                    if "Maximum" in v and "SampleValue" not in v:
                        v["SampleValue"] = sampleString[:int(v["Maximum"])]

                # enforce regex for integer when no pattern provided
                if "Type" in v:
                    if v["Type"] == "Integer":
                        if "Pattern" not in v and "Minimum" in v and "Maximum" in v:
                            template = "^[%s,%s]}$"
                            constrainedString = template % (int(v["Minimum"]), int(v["Maximum"]))
                            v["Pattern"] = constrainedString
                            v["SampleValue"] = "%s...%s" % (int(v["Minimum"]), int(v["Maximum"]))
                            log.debug(constrainedString)

                # coerce pipe separated string values into unique list e.g.  "Allowed values": "CA_REPOSITORY | RESOURCE_PKI_MANIFEST | RESOURCE_PKI_NOTIFY",
                if "AllowedValues" in v and type(v["AllowedValues"]) == str:
                    v["AllowedValues"] = sorted(list(set(v["AllowedValues"].split(" | "))))


                if "AllowedValues" in v and "SampleValue" not in v:
                    # v["SampleValue"] = sorted(v["AllowedValues"])[0]
                    v["SampleValue"] = "|".join(v["AllowedValues"])
                    if "Pattern" not in v:
                        v["Pattern"] = "^[%s]" % (v["SampleValue"])


                v['PropertyKey'] = k.split('.')[-1]
                v['ServiceKey'] = k.split('.')[0]
                v['ParentKey'] = k.split('.')[0]

            else:
                log.warn(k)
                log.warn(json.dumps(v, indent=4))

            if "aws-properties-" in k:
                k = k.replace("aws-properties-","").replace("-properties","-cfnproperties").replace('-','.')
                v = list(v.keys())
                properties[k.lower()] = v
            else:

                properties[k.lower()] = v
        except Exception as e:
            # not the droids keep on trucking
            log.warning(e)

log.info("%s properties files processed" % (len(files)))

log.debug(json.dumps(properties, indent=4))

output_file = 'allowed_values.json'
with open(output_file, 'w') as file:
    file.write(json.dumps(properties, indent=4, sort_keys=True))
    file.close()
    log.info("Written: %s" % (output_file))

for cfn_resource in resource_rules.keys():
    rule_file = "./rulesets/v2/%s.guard.txt" % (inflection.paramatize(cfn_resource.lower()))
    with open(rule_file, 'w') as f:
        f.write(json.dumps(resource_rules[cfn_resource], indent=4))
        log.info("Written: %s" % (rule_file))
        f.close()