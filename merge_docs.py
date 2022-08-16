import json
import os
import sys
import inflection
import glob
import logging
import sys
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

cfn = {}
guard = {}
outfile = 'CloudFormationResourceSpecificationAll.json'
cfn_src = json.load(open('CloudFormationResourceSpecificationWithIcons.json'))

cfn_src["PropertyTypes"]["String"] = {
    "Description": "A String",
    "Pattern": "^[\\w#:\\.\\-/]+$",
    "SampleValue": "SampleString"
  }

cfn_src["PropertyTypes"]["Boolean"] = {
    "Description": "A Boolean",
    "AllowedValues": "True|False",
    #"Pattern": "^(?:tru|fals)e$",\
    "Pattern": "^(True|False)$",
    "SampleValue": "True"
}
cfn_src["PropertyTypes"]["Integer"] = {
    "Description": "A Integer",
    "Pattern": "/^[-+]?\d+$/", # https://stackoverflow.com/questions/9043551/regex-that-matches-integers-in-between-whitespace-or-start-end-of-string-only
    #"Minimum": "-2147483648",
    #"Maximum": "2147483647"    
    "SampleValue": "999999999"
}
cfn_src["PropertyTypes"]["Long"] =  {
    "Description": "A Long",
    # Pattern LONG_PATTERN = Pattern.compile("^-?\\d{1,19}$"); https://stackoverflow.com/questions/11243204/how-to-match-a-long-with-java-regex
    "Pattern": "^-?\\d{1,19}$",
    # "Minimum": "-9223372036854775808",
    # "Maximum": "9223372036854775807"
    "SampleValue": "999999999999999999"
}
cfn_src["PropertyTypes"]["Double"] = {
    "Description": "A Double",
    "Pattern": "/^[0-9]+(\\.[0-9]+)?$", # https://stackoverflow.com/questions/10516967/regexp-for-a-double
    # "Minimum": "1",
    # "Maximum": "255"
    "SampleValue": "99.99"
}
cfn_src["PropertyTypes"]["Float"] = {
    "Description": "A Float",
    "Pattern": "^([+-]?\\d*\\.?\\d*)$", # https://stackoverflow.com/questions/6754552/regex-to-find-a-float
    # "Minimum": "1",
    # "Maximum": "255"
    "SampleValue": "9.9999999999"
}
cfn_src["PropertyTypes"]["Json"] = {
    "Pattern": '(?(DEFINE)(?<json>(?>\s*(?&object)\s*|\s*(?&array)\s*))(?<object>(?>\{\s*(?>(?&pair)(?>\s*,\s*(?&pair))*)?\s*\}))(?<pair>(?>(?&STRING)\s*:\s*(?&value)))(?<array>(?>\[\s*(?>(?&value)(?>\s*,\s*(?&value))*)?\s*\]))(?<value>(?>true|false|null|(?&STRING)|(?&NUMBER)|(?&object)|(?&array)))(?<STRING>(?>"(?>\\(?>["\\\/bfnrt]|u[a-fA-F0-9]{4})|[^"\\\0-\x1F\x7F]+)*"))(?<NUMBER>(?>-?(?>0|[1-9][0-9]*)(?>\.[0-9]+)?(?>[eE][+-]?[0-9]+)?)))\A(?&json)\z'
}
cfn_src["PropertyTypes"]["Timestamp"] = "1970-01-01T01:02:30.070Z"
cfn_src["PropertyTypes"]["Tags"] = [
    {
        "Key": "keyName",
        "Value": "valueName"
    }
]


#cfn_out = json.load(open('CloudFormationResourceSpecificationWithIcons.json'))
cfn_selectors = {}
aws_docs_ref = {}
allowed_values = json.load( open('allowed_values.json'))

def ingest_documentation( item ):
    global aws_docs_ref
    if type(item) is dict:
        if 'Documentation' in item and "Properties" in item:
            url = item['Documentation']
            item['Selector'] = url.split('/aws-properties-')[-1].split('.html')[0]
            if url not in aws_docs_ref:
                aws_docs_ref[url] = item # ["Properties"]
                log.info("Ingested DOCS-Ref: %s" % (url))
        
        if "Properties" in item:
            for k, v in item["Properties"].items():
                if k not in aws_docs_ref[url]:
                    aws_docs_ref[url][k] = v
                    log.info("Amended DOCS-Ref: %s: %s" % (k, v))
                    ingest_documentation(v)
                
            

## Add Regional Support 
for file in glob.glob("aws-cfn-resource-specs/specs/*/CloudFormationResourceSpecification.json"):
    log.debug("Processing CFN Spec: %s" %(file))
    region = file.rstrip('.json').split('aws-cfn-resource-specs/specs/')[1].split('/')[0].lower().strip()
    log.debug(region)
    with open(file, 'r') as schema:
        cfn[region] = json.load(schema)
        log.debug("Loading cfn for : %s" % (region))


cfn_out = cfn["us-east-1"]
log.info("Set global spec to us-east-1")
log.info("Assessing resource availability in regions [%s]" % (
    ",".join(cfn.keys())))

for resource in cfn_out["ResourceTypes"].keys():
    log.debug("Processing Regions for Resource: %s" % (resource))
    cfn_out["ResourceTypes"][resource]["RegionSupport"] = []
    for region in cfn.keys():
        if resource in cfn[region]["ResourceTypes"]:
            cfn_out["ResourceTypes"][resource]["RegionSupport"].append(
                region)
            log.debug("\tAdding Region: %s" % (region))

## Add AWS_DOCS based PropertyTypes missing
for property_file in glob.glob("doc_source/aws-properties*.json"):
    property_data = json.load(open(property_file))
    for k, v in property_data.items():
        # store the dotNotated Property Name with value in PropertyTypes if not present
        if k not in cfn_out['PropertyTypes']:
            cfn_out['PropertyTypes'][k] = v
            cfn_selectors[k] = property_file
            log.debug("Added Property Type: %s" % k)

            if "Documentation" in v:
                aws_docs_ref[v["Documentation"]] = v
                log.info("Added AWS Docs Ref: %s" % v["Documentation"])
        
        else: # append any properties in docs but not in schema 
            for k2, v2 in v.items():
                if k2 not in cfn_out['PropertyTypes'][k]:
                    cfn_out['PropertyTypes'][k][k2] = v2
                    log.debug("Added Property Attribute: %s.%s" % (k, k2))

                    ingest_documentation( v2 )
        
        # store the raw Property Name as well as dotNotated resource PropertyName
        kPropertyName = k.split('.')[-1]
        if kPropertyName not in cfn_out['PropertyTypes']:
            v['Selector'] = k
            cfn_out['PropertyTypes'][kPropertyName] = v
            log.debug("Added Property Name: %s" % kPropertyName)
            
# Generate Guard matches/selectors

for resource, resource_data in cfn_src['ResourceTypes'].items():

    resource_split = resource.split('::') 
    resource_stubs = resource_split.copy()
    resource_stubs.pop(0)
    resource_stubs = '.'.join(resource_stubs)
    cfn_selectors[resource_stubs.lower()] = resource

    log.info("[%s]\t%s" % (resource, resource_stubs) )

    if "Documentation" in resource_data:
        filename = resource_data['Documentation'].split('.html')[0].split('/')[-1]
        filepath = "./doc_source/%s.md.properties.json" % (filename)
        resource_docs_data = json.load(open(filepath))
        log.info("Loading DOCs: %s" % filepath)
        ingest_documentation( resource_docs_data )

   
    #log.info("CFN Specication data")
    #log.info(json.dumps(cfn_src['ResourceTypes'][resource]["Properties"],indent=4))
    docs_processed = False

    for property_name, property_data in cfn_src['ResourceTypes'][resource]["Properties"].items():
        log.info('\t%s.%s' % (resource, property_name) )
        ingest_documentation( property_data )
        property_stub = "%s.%s" % (resource_stubs.lower(), property_name) 
        cfn_selectors[property_stub] = "%s.%s" % (resource, property_name)
        property_type = "%s.%s" % (resource, property_name)
        log.debug(json.dumps(property_data, indent=4))
        if "Documentation" in property_data and not docs_processed:

            filename = property_data["Documentation"].split('.html')[0].split('/')[-1]
            filepath = "./doc_source/%s.md.properties.json" % (filename)
            log.info("Loading DOCs: %s" % filepath)
            property_docs_data = json.load(open(filepath)) #[property_name]
            keys = list(property_docs_data.keys())

            for k  in keys:
                v = property_docs_data[k]

                ingest_documentation( property_docs_data[k] )
                property_name = k.split('.')[-1] # property name only
                property_docs_data[property_name] = v
                property_docs_data[property_name]['Selector'] = k
                if k not in cfn_out['PropertyTypes']:
                    cfn_out['PropertyTypes'][k] = v
                    log.info('Adding Property: %s' % k )
                    ingest_documentation( v )
                #else:
                #    for k2, v2 in v.items():
                #        if k2 not in cfn_out['PropertyTypes'][k]:
                #            cfn_out['PropertyTypes'][k][k2] = v2
                #            log.info('Adding Property: %s.%s' % (k, k2) )
                #            ingest_documentation( v2 )
                    
                del property_docs_data[k]

                if property_name not in cfn_out['ResourceTypes'][resource]["Properties"]:
                    log.info("ADDED: %s.%s" % (resource, property_name))
                    cfn_out['ResourceTypes'][resource]["Properties"][property_name] = v
                else:
                    for k3, v3 in v.items():
                        if k3 not in cfn_out['ResourceTypes'][resource]["Properties"][property_name]:
                            log.info("DEPTH CHECK: %s.%s.%s" % (resource, property_name, k3))
                            cfn_out['ResourceTypes'][resource]["Properties"][property_name][k3] = v3
                            ingest_documentation( v3 )

            docs_processed = True


# generate guard skeleton
for k, v in cfn_out['PropertyTypes'].items():

    ingest_documentation( v )

    if '::' in k: # Has Resource::Name Syntax
        resource_type = k.split('.')[0] # ResouceType
        dotNotated = k.replace('%s.' % (resource_type), "") # Remove 'Resource::Type.'
        split_resource = resource_type.lower().split('::') # create resource name stub 
        split_resource.pop(0) # discard first entry
        resource_stub = '.'.join(split_resource) + '.' + dotNotated # resource.type.dot.notation
        
        if resource_type not in guard:
            guard[resource_type] = {}
        
        if "Properties" in cfn_out['PropertyTypes'][k]:
            for k2, v2 in cfn_out['PropertyTypes'][k]["Properties"].items():
                # property_key = "%s.%s" % (resource_stub, k2)
                selector = "%s.%s" % (dotNotated, k2)
                # additions[property_key] = v2
                guard[resource_type][selector] = v2
                if "Documentation" in v2:
                    doc_data_found = v2["Documentation"] in aws_docs_ref

                    if not doc_data_found:
                        log.info("[%s] \t %s: %s" % (doc_data_found, selector, v2["Documentation"]))
                    else:
                        log.info(json.dumps(aws_docs_ref[v2["Documentation"]], indent=4))
                        for docK, docV in aws_docs_ref[v2["Documentation"]].items():
                            if docK not in guard[resource_type][selector]:
                                guard[resource_type][selector][docK] = docV
                                log.info("Added: %s.%s.%s" % (resource_type, selector, docK))

                log.debug("Guard  %s.%s" % (resource_type, selector))

with open(outfile, 'w') as filehandle:
    json.dump(cfn_out, filehandle, indent=4, sort_keys=True)
    log.info("Written:$%s" % ( outfile ))
    filehandle.close()
    
#aws_docs_ref 
outfile = 'aws_docs_ref.json'
with open(outfile, 'w') as filehandle:
    json.dump(aws_docs_ref, filehandle, indent=4, sort_keys=True)
    log.info("Written:$%s" % ( outfile ))
    filehandle.close()

#guard 
outfile = 'guard_selectors.json'
with open(outfile, 'w') as filehandle:
    json.dump(guard, filehandle, indent=4, sort_keys=True)
    log.info("Written:$%s" % ( outfile ))
    filehandle.close()
