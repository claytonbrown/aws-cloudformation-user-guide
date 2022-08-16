import json
import logging
from colorlog import ColoredFormatter
import glob
import sys
import os
import chevron
import exrex
import inflection
from enum import Enum

class RuleTypes(Enum):
    REQUIRED = 'required'
    ALLOWED = 'allowed'
    PATTERN = 'regex'
    RANGE = 'range'
    PREVENTED = 'prevented'
    SAMPLE = 'sample'


rt = RuleTypes
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


required_rule = """rule {{rule_name}}_Exists {
\t%{{ property_name }} exists
}
"""

range_rule = """
rule {{rule_name}}Range
{
    # 
    # {{notes}}
    #
    let selected_{{property_name}}_values  = configuration.ipPermissions[ 
        some ipv4Ranges[*].cidrIp == "0.0.0.0/0" or
        some ipv6Ranges[*].cidrIpv6 == "::/0"
        ipProtocol != 'udp' 
    ]
    
    when %selected_{{property_name}}_values !empty
    {
        %any_ip_permissions {
            {{selector}} {
                {{property_name}} > {{max}} or 
                {{property_name}}   < {{min}} 
                <<
                    result: NON_COMPLIANT
                    message: {{property_name}}t was not in allowed range: [{{min}}-{{max}}]
                >>
            }                
        }
    }
}
"""

allowed_rule = """let allowed_{{property_name}}_values = [{{ allowed_values }}]
rule {{rule_name}} when {{property_name}} !empty {
let value = %s.Properties.{{property_name}}
%{{ property_name }} exists
\t%{{ guard_selector}} in allowed_{{property_name}}_values
\n}
"""

not_allowed_rule = """let not_allowed_{{property_name}}_values = [{{ allowed_values }}]
rule {{rule_name}} when {{property_name}} !empty {
let value = %s.Properties.{{property_name}}
%{{ property_name }} exists
\t%{{ guard_selector}} not in not_allowed_{{property_name}}_values
}
"""

sample_rule = """let sample_{{property_name}} = [{{ allowed_values }}]
rule {{rule_name}} when {{property_name}} !empty {
let value = %s.Properties.{{property_name}}
%{{ property_name }} exists
\t%{{ guard_selector}} in sample_{{property_name}}
}
""" 


resource_rules = {}

cfn_selectors = {}

def add_rule(        
        cfn_resource, # = 'AWS::S3::Bucket',
        cfn_property, # = 'SSEAlgorithm',
        guard_selector, #='encryption.ServerSideEncryptionConfiguration[*].ServerSideEncryptionByDefault.SSEAlgorithm',                
        allowed_values_string=None, # ['AES256','aws:kms']      
        rule_name=None,
        rule_type=rt.SAMPLE,   
        references=[]
        ):

    if rule_name is None:
        rule_name = 'Rule_%s_%s' % (
            cfn_resource.replace('::','_'),
            cfn_property
        )

    rule_mapping = {
        rt.REQUIRED: required_rule,
        rt.ALLOWED: allowed_rule,
        rt.PREVENTED: not_allowed_rule,
        rt.SAMPLE: sample_rule
    }

    args = {
        'template': rule_mapping[rule_type],

        'data': {
            'resource_type': cfn_resource,                  # e.g. 'AWS::S3::Bucket'
            'property_name': cfn_property,                  # e.g. %encryption exists
            'rule_name':  rule_name,                        # aws_resouce_name_property_rule
            'matcher_rule': guard_selector,                     # e.g. %encryption.ServerSideEncryptionConfiguration[*].ServerSideEncryptionByDefault.SSEAlgorithm
            'allowed_values': allowed_values_string         # e.g. ['value1','value2','etc']
        }
    }
    rule = chevron.render(**args)
    log.info(rule)
    if cfn_resource not in resource_rules:
        resource_rules[cfn_resource] = {
            rt.REQUIRED: [],
            rt.ALLOWED: [],
            rt.PREVENTED: [],
            rt.SAMPLE: []
        }
    resource_rules[cfn_resource][rule_type].append(rule)

sampleString = "abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 500

# aws-properties-autoscalingplans-scalingplan-scalinginstruction.md:*Allowed Values*: `KeepExternalPolicies | ReplaceExternalPolicies`
properties = {}

cfn_schema = json.load(open('CloudFormationResourceSpecification.json','r'))
schema_key = {}
for resource_name, resource_properties in cfn_schema["ResourceTypes"].items():
    key = resource_name #.replace('::','.')
    schema_key[key] = resource_name
    log.info("%s --> %s" % (key, resource_name))


    # create CNF guard 2 resource selector
    cfn_selectors[resource_name] = {}

    if "Properties" in resource_properties:
        for resource_property_name, resource_property_detail in resource_properties["Properties"].items():
            property_key = "%s.%s" % (key, resource_property_name)
            property_ref = "%s.%s" % (resource_name, resource_property_name)
            schema_key[property_key] = property_ref
            log.info("%s --> %s" % (property_key, property_ref))
            cfn_selectors[resource_name][resource_property_name]= {}



            # EXISTS RULES
            if "Required" in resource_property_detail and resource_property_detail['Required']:
                add_rule(
                    cfn_resource = resource_name,
                    cfn_property = resource_property_name,
                    guard_selector=resource_property_name,
                    allowed_values_string=None,
                    rule_type=rt.REQUIRED
                )

            # ALLOWED RULES

            # NOT ALLOWED RULES

            # EXPECTED RULES

files = glob.glob('doc_source/aws-properties-*.md.properties.json')
for file in files:

    log.debug(file)
    data = json.load(open(file,'r'))
    for k, v in data.items():

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
        
        elif "CfnAbout" in key or "CfnType" in key or "CfnDocsKey" in key:
            subKey = k.split('.')[-1]
            prefixKey = key.replace('.'+subKey, '')
            properties[prefixKey][subKey] = v
        else:
            properties[k] = v
            #properties[k.lower()] = v
            try:
                propertyName = k.split('.')[-1]
                resourcType = properties[k.replace('.'+propertyName, 'CfnType')]
                properties[k]['ResourceType'] = resourcType
            except Exception as e: 
                print(e)

log.info("%s properties files processed" % (len(files)))

log.debug(json.dumps(properties, indent=4))

output_file = 'allowed_values.json'
with open(output_file, 'w') as file:
    file.write(json.dumps(properties, indent=4, sort_keys=True))
    file.close()
    log.info("Written: %s" % (output_file))






for cfn_resource in resource_rules.keys():
    for rule_type, value in resource_rules[cfn_resource].items():
        rule_file = "./rulesets/v2/%s/%s.guard.txt" % (rule_type.value, inflection.underscore(cfn_resource.lower()))
        os.makedirs(rule_file.replace(rule_file.split('/')[-1],''), exist_ok=True)
        with open(rule_file, 'w') as f:
            rule = """let resources = Resources.*[ Type == %s ]\n\n%s""" % (cfn_resource, '\n'.join(resource_rules[cfn_resource][rule_type]))
            f.write(rule)
            log.info("Written: %s" % (rule_file))
            f.close()


# EXPLORE ICONS 
icon_files = glob.glob("")        