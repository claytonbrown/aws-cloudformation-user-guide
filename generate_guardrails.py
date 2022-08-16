import json
import os
import sys
import inflection
import glob
import logging
import sys
from colorlog import ColoredFormatter

def setup_logging():
    log = logging.getLogger(__name__)
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
    return log

log = setup_logging()


rules = []
sample_guard = """
let matched_resources = Resources.*[ Type == '{resource_type}' ]

{rules}
"""
# file: {rule_file}

sample_rule = """
rule {rule_name} when %matched_resources !empty {{
    %matched_resources.Properties {{
        {property_name} {rule_operator} {rule_value}
        <<{failure_message} [{citations}]>>
    }}
}}
"""

rules.append(
    sample_rule.format(
        rule_name = "rule_name",
        property_name = "property_name",
        rule_operator = "==",
        rule_value = "rule_value",
        failure_message = "failure_message",
        citations = "[cite1,cite2]" 
    )
)

rules.append(
    sample_rule.format(
        rule_name = "rule_name",
        property_name = "property_name",
        rule_operator = "!=",
        rule_value = "rule_value",
        failure_message = "failure_message",
        citations = "[cite1,cite2]" 
    )
)

rules.append(
    sample_rule.format(
        rule_name = "rule_name",
        property_name = "property_name",
        rule_operator = "<",
        rule_value = "rule_value",
        failure_message = "failure_message",
        citations = "[cite1,cite2]" 
    )
)

print(
    sample_guard.format(
        rule_file = "rule_file",
        resource_type = "AWS::Resource::Type",
        rules = "\n".join(rules)
    )
)

class CfnSchemaEnricher():

    cfn = {}
    cfn_spec = {}
    cfn_selectors = {}
    guardrails = {}
    aws_docs_ref = {}
    allowed_values = {}
    glob_cfn_schemas=None

    def __init__(self, glob_cfn_schemas="aws-cfn-resource-specs/specs/*/CloudFormationResourceSpecification.json"):
        self.allowed_values = json.load( open('allowed_values.json'))
        self.glob_cfn_schemas = glob_cfn_schemas


    def load_enriched_cfn(self):

        self.cfn_spec = json.loads(open('CloudFormationResourceSpecification.json','r').read())

        self.cfn_spec["PropertyTypes"]["string"] = {
            "Description": "A String",
            "Pattern": "^[\\w#:\\.\\-/]+$",
            "SampleValue": "SampleString"
        }

        self.cfn_spec["PropertyTypes"]["boolean"] = {
            "Description": "A Boolean",
            "AllowedValues": "True|False",
            "Pattern": "^(True|False)$",
            "SampleValue": "True"
        }
        self.cfn_spec["PropertyTypes"]["integer"] = {
            "Description": "A Integer",
            "Pattern": "/^[-+]?\d+$/", # https://stackoverflow.com/questions/9043551/regex-that-matches-integers-in-between-whitespace-or-start-end-of-string-only
            "SampleValue": "999999999"
        }
        self.cfn_spec["PropertyTypes"]["long"] =  {
            "Description": "A Long",
            "Pattern": "^-?\\d{1,19}$", # https://stackoverflow.com/questions/11243204/how-to-match-a-long-with-java-regex
            "SampleValue": "999999999999999999"
        }
        self.cfn_spec["PropertyTypes"]["double"] = {
            "Description": "A Double",
            "Pattern": "/^[0-9]+(\\.[0-9]+)?$", # https://stackoverflow.com/questions/10516967/regexp-for-a-double
            "SampleValue": "99.99"
        }
        self.cfn_spec["PropertyTypes"]["float"] = {
            "Description": "A Float",
            "Pattern": "^([+-]?\\d*\\.?\\d*)$", # https://stackoverflow.com/questions/6754552/regex-to-find-a-float
            "SampleValue": "9.9999999999"
        }
        self.cfn_spec["PropertyTypes"]["json"] = {
            "Pattern": '(?(DEFINE)(?<json>(?>\s*(?&object)\s*|\s*(?&array)\s*))(?<object>(?>\{\s*(?>(?&pair)(?>\s*,\s*(?&pair))*)?\s*\}))(?<pair>(?>(?&STRING)\s*:\s*(?&value)))(?<array>(?>\[\s*(?>(?&value)(?>\s*,\s*(?&value))*)?\s*\]))(?<value>(?>true|false|null|(?&STRING)|(?&NUMBER)|(?&object)|(?&array)))(?<STRING>(?>"(?>\\(?>["\\\/bfnrt]|u[a-fA-F0-9]{4})|[^"\\\0-\x1F\x7F]+)*"))(?<NUMBER>(?>-?(?>0|[1-9][0-9]*)(?>\.[0-9]+)?(?>[eE][+-]?[0-9]+)?)))\A(?&json)\z'
        }
        self.cfn_spec["PropertyTypes"]["timestamp"] = "1970-01-01T01:02:30.070Z"

        self.cfn_spec["PropertyTypes"]["tags"] ={
            "Pattern": '(?(DEFINE)(?<json>(?>\s*(?&object)\s*|\s*(?&array)\s*))(?<object>(?>\{\s*(?>(?&pair)(?>\s*,\s*(?&pair))*)?\s*\}))(?<pair>(?>(?&STRING)\s*:\s*(?&value)))(?<array>(?>\[\s*(?>(?&value)(?>\s*,\s*(?&value))*)?\s*\]))(?<value>(?>true|false|null|(?&STRING)|(?&NUMBER)|(?&object)|(?&array)))(?<STRING>(?>"(?>\\(?>["\\\/bfnrt]|u[a-fA-F0-9]{4})|[^"\\\0-\x1F\x7F]+)*"))(?<NUMBER>(?>-?(?>0|[1-9][0-9]*)(?>\.[0-9]+)?(?>[eE][+-]?[0-9]+)?)))\A(?&json)\z',
            "SampleValue": [
                {
                    "Key": "TagName1",
                    "Value": "TagValue1"
                },
                {
                    "Key": "TagName2",
                    "Value": "TagValue2"
                }
            ]
        }

        ## Add Regional Support 
        
        for file in glob.glob(self.glob_cfn_schemas):
            log.debug("Processing CFN Spec: %s" %(file))
            region = file.rstrip('.json').split('aws-cfn-resource-specs/specs/')[1].split('/')[0].lower().strip()
            log.debug(region)
            with open(file, 'r') as schema:
                self.cfn[region] = json.load(schema)
                log.debug("Loading cfn for : %s" % (region))


        self.cfn_out = self.cfn["us-east-1"]
        log.info("Set global spec to us-east-1")
        log.info("Amended resource availability for %s regions" % (len(self.cfn.keys())))
        log.debug(",".join(self.cfn.keys()))

        ## Add Regional Support
        for resource in self.cfn_out["ResourceTypes"].keys():
            log.debug("Processing Regions for Resource: %s" % (resource))
            self.cfn_out["ResourceTypes"][resource]["RegionSupport"] = []
            for region in self.cfn.keys():
                if resource in self.cfn[region]["ResourceTypes"]:
                    self.cfn_out["ResourceTypes"][resource]["RegionSupport"].append(region)
                    log.debug("\tAdding Region: %s" % (region))
        
        ## Normalize existing PropertyTypes to lowercase 
        for k, v in self.cfn_spec['PropertyTypes'].items():     # iterate spec not output, mutate output
            if '::' in k:
                resource = k.split('.')[0]                      # seperate RESOURCE::TYPE.FromProperty
                split_resource = resource.lower().split('::')   # split into dot parts
                split_resource.pop(0)                           # discard first name AWS:: etc 
                resource_stub = '.'.join(split_resource)        # dot notate 
                self.cfn_selectors[resource_stub] = resource    # map resource.type TO Resource::Type
                self.cfn_selectors[resource] = resource_stub    # map Resource::Type TO resource.type
                self.ingest_types(v, resource_stub)             # record each resource.type.property
                del self.cfn_out['PropertyTypes'][k]            # Discard complex/nested type definitions
        
        ## Add AWS_DOCS based PropertyTypes information
        count = 0
        for aws_docs in glob.glob("doc_source/aws-properties*.md.properties.json"):
            count +=1 
            property_data = json.load(open(aws_docs))
            for k, v in property_data.items():
                self.ingest_types(v, k)
                if k not in self.cfn_out:
                    log.debug("Amending Properties with property: [%s]\n%s" % (k, v))
                    self.cfn_out[k] = v
                else:
                    log.warn("Collision Properties with property: %s")
                    log.debug()
        log.info("Ingested %s aws docs properties files : %s PropertyTypes" % (count, len(self.cfn_out['PropertyTypes'])))

        ## Add AWS_DOCS based ResourceTypes information
        count = 0
        for aws_docs in glob.glob("doc_source/aws-resource-*.md.properties.json"):
            count +=1
            property_data = json.load(open(aws_docs))
            for k, v in property_data.items():
                self.ingest_types(v, k)
                self.cfn_out[k] = v
        log.info("Ingested %s aws docs resource files : %s ResourceTypes" % (count, len(self.cfn_out['ResourceTypes'])))
        log.info(
            json.dumps(sorted(list(self.cfn_out['PropertyTypes'].keys())), indent=4)
        )

    def ingest_types(self, item, selector=None ):
        if type(item) is dict:
            if selector is not None:
                selectorKey = selector.lower()
                if selectorKey in self.cfn_out['PropertyTypes']:
                    log.debug("Existing property: %s" % (selectorKey))
                    for k, v in item.items():
                        if k not in self.cfn_out['PropertyTypes'][selectorKey]:
                            self.cfn_out['PropertyTypes'][selectorKey][k] = v
                        elif v == self.cfn_out['PropertyTypes'][selectorKey][k]:
                            pass
                        else:
                            log.debug(
                                json.dumps(
                                    { 
                                        "old": self.cfn_out['PropertyTypes'][selectorKey][k],
                                        "new": v
                                    }, 
                                    indent=4)
                            )
                            # keep longest property
                            if type(v) is bool or type(self.cfn_out['PropertyTypes'][selectorKey][k]) is bool:
                                pass
                            elif len(v) > len(self.cfn_out['PropertyTypes'][selectorKey][k]):
                                self.cfn_out['PropertyTypes'][selectorKey][k] = v
                            log.debug("Conflict [%s.%s] Longest value: %s" % (selectorKey, k, self.cfn_out['PropertyTypes'][selectorKey][k]))
                else:
                    self.cfn_out['PropertyTypes'][selectorKey] = item
            
            if 'Documentation' in item and "Properties" in item:
                url = item['Documentation'].lower().strip()
                item['aws_docs'] = url.split('/aws-properties-')[-1].split('/aws-resources-')[-1].split('.html')[0]
                if url not in self.aws_docs_ref:
                    self.aws_docs_ref[url] = item # ["Properties"]
                    log.debug("Ingested DOCS-Ref: %s" % (url))

            if "Properties" in item:
                for k, v in item["Properties"].items():
                    if k not in self.aws_docs_ref[url]:
                        self.aws_docs_ref[url][k] = v
                        log.debug("Amended DOCS-Ref: %s: %s" % (k, v))
                        selector = "%s.%s" % (selector, k)
                        self.ingest_types(v, selector)
        else:
            log.warn(json.dumps(item))
                    
                

    def process_aws_cfn_docs(self):

        for resource, resource_data in self.cfn_spec['ResourceTypes'].items():

            # calculate stubs
            resource_split = resource.split('::') 
            resource_stubs = resource_split.copy()
            resource_stubs.pop(0)
            resource_stub = '.'.join(resource_stubs).lower()
            self.cfn_selectors[resource_stub] = resource
            log.info("[%s]\t%s" % (resource, resource_stub) )

            if "Documentation" in resource_data:
                filename = resource_data['Documentation'].split('.html')[0].split('/')[-1]
                filepath = "./doc_source/%s.md.properties.json" % (filename)
                resource_docs_data = json.load(open(filepath))
                resource_markdown = open(filepath,replace('.md.properties.json','.md')).read()
                resource_type = resource_markdown[0].split(' ')[1]
                log.info("Loading DOCs: %s" % filepath)
                ingest_documentation( resource_docs_data, resource_type )

        
            #log.info("CFN Specication data")
            #log.info(json.dumps(self.cfn_spec['ResourceTypes'][resource]["Properties"],indent=4))
            docs_processed = False # only ingest aws_docs for initial properties not each (#anchors in same docs)

            for property_name, property_data in self.cfn_spec['ResourceTypes'][resource]["Properties"].items():
                log.info('\t%s.%s' % (resource, property_name) )
                self.ingest_types( property_data )

                property_stub = "%s.%s" % (resource_stubs.lower(), property_name) 
                self.cfn_selectors[property_stub] = "%s.%s" % (resource, property_name)

                property_type = "%s.%s" % (resource, property_name)
                log.debug(json.dumps(property_data, indent=4))
                
                if "Documentation" in property_data and not docs_processed:

                    filename = property_data["Documentation"].split('.html')[0].split('/')[-1]
                    filepath = "./doc_source/%s.md.properties.json" % (filename)
                    log.info("Loading DOCs: %s" % filepath)
                    property_docs_data = json.load(open(filepath)) #[property_name]
                    keys = list(property_docs_data.keys())

                    for k, v  in property_docs_data.items():

                        self.ingest_types(v)

                        property_name = k.split('.')[-1] # property name only
                        self.property_docs_data[property_name] = v
                        self.property_docs_data[property_name]['Resource'] = resource
                        self.property_docs_data[property_name]['ResourceStub'] = resource_stubs.lower()
                        self.property_docs_data[property_name]['Selector'] = k
                        if k not in self.cfn_out['PropertyTypes']:
                            self.cfn_out['PropertyTypes'][k] = v
                            log.info('Adding Property: %s' % k )
                            ingest_documentation( v )
                        #else:
                        #    for k2, v2 in v.items():
                        #        if k2 not in self.cfn_out['PropertyTypes'][k]:
                        #            self.cfn_out['PropertyTypes'][k][k2] = v2
                        #            log.info('Adding Property: %s.%s' % (k, k2) )
                        #            ingest_documentation( v2 )
                            
                        del property_docs_data[k]

                        if property_name not in self.cfn_out['ResourceTypes'][resource]["Properties"]:
                            log.info("ADDED: %s.%s" % (resource, property_name))
                            self.cfn_out['ResourceTypes'][resource]["Properties"][property_name] = v
                        else:
                            for k3, v3 in v.items():
                                if k3 not in self.cfn_out['ResourceTypes'][resource]["Properties"][property_name]:
                                    log.info("DEPTH CHECK: %s.%s.%s" % (resource, property_name, k3))
                                    self.cfn_out['ResourceTypes'][resource]["Properties"][property_name][k3] = v3
                                    ingest_documentation( v3 )

                    docs_processed = True


    def generate_guard_skeleton(self):
        # generate guard skeleton
        for k, v in self.cfn_out['PropertyTypes'].items():

            self.ingest_types( v )

            if '::' in k: # Has Resource::Name Syntax
                resource_type = k.split('.')[0] # ResouceType
                dotNotated = k.replace('%s.' % (resource_type), "") # Remove 'Resource::Type.'
                split_resource = resource_type.lower().split('::') # create resource name stub 
                split_resource.pop(0) # discard first entry
                resource_stub = '.'.join(split_resource) + '.' + dotNotated # resource.type.dot.notation
                
                if resource_type not in self.guardrails:
                    self.guardrails[resource_type] = {}
                
                if "Properties" in self.cfn_out['PropertyTypes'][k]:
                    for k2, v2 in self.cfn_out['PropertyTypes'][k]["Properties"].items():
                        # property_key = "%s.%s" % (resource_stub, k2)
                        selector = "%s.%s" % (dotNotated, k2)
                        self.guardrails[resource_type][selector] = v2
                        if "Documentation" in v2:
                            doc_data_found = v2["Documentation"] in self.aws_docs_ref

                            if not doc_data_found:
                                log.info("[%s] \t %s: %s" % (doc_data_found, selector, v2["Documentation"]))
                            else:
                                log.info(json.dumps(self.aws_docs_ref[v2["Documentation"]], indent=4))
                                for docK, docV in self.aws_docs_ref[v2["Documentation"]].items():
                                    if docK not in guard[resource_type][selector]:
                                        self.guardrails[resource_type][selector][docK] = docV
                                        log.info("Added: %s.%s.%s" % (resource_type, selector, docK))

                        log.debug("Guard  %s.%s" % (resource_type, selector))


    def save_outputs(self):
        self.save_self.aws_docs_ref()
        self.save_enriched_schema()
        self.save_self.guardrails_ref()

    def save_enriched_schema(self, outfile = 'cfn_enriched.json'):
        with open(outfile, 'w') as filehandle:
            json.dump(self.cfn_out, filehandle, indent=4, sort_keys=True)
            log.info("Written:$%s" % ( outfile ))
            filehandle.close()
            
    def save_aws_docs_ref(self, outfile = 'aws_docs_ref.json'):
        
        with open(outfile, 'w') as filehandle:
            json.dump(self.aws_docs_ref, filehandle, indent=4, sort_keys=True)
            log.info("Written:$%s" % ( outfile ))
            filehandle.close()

    def save_guardrails_ref(self, outfile = 'guard_selectors.json'):

        with open(outfile, 'w') as filehandle:
            json.dump(self.guardrails, filehandle, indent=4, sort_keys=True)
            log.info("Written:$%s" % ( outfile ))
            filehandle.close()

        """_summary_
        "AWS::ACMPCA::Certificate": {
            "ApiPassthrough.Extensions": {
                "Documentation": "http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-acmpca-certificate-apipassthrough.html#cfn-acmpca-certificate-apipassthrough-extensions",
                "Required": false,
                "Type": "Extensions",
                "UpdateType": "Immutable"
            },
            "ApiPassthrough.Subject": {
                "Documentation": "http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-acmpca-certificate-apipassthrough.html#cfn-acmpca-certificate-apipassthrough-subject",
                "Required": false,
                "Type": "Subject",
                "UpdateType": "Immutable"
            },
        """

        for resource, properties in self.guardrails.items():
            guard_file = './guardrails/required/%s.guard' % (inflection.underscore(resource))
            log.info('Generating guard rail: %s' % (guard_file))

            rules = []

            for selector, data in properties.items():


        


if __name__ == "__main__":
    cse = CfnSchemaEnricher()
    cse.load_enriched_cfn()
    cse.save_enriched_schema()
    cse.save_aws_docs_ref()
    cse.save_guardrails_ref()