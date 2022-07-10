import json
import os
import sys

cfn = json.load(open('CloudFormationResourceSpecification.json'))

allowed_values = json.load( open('allowed_values.json'))

#
# ./doc_source/aws-resource-workspaces-workspace.md.properties.json
# ./doc_source/aws-properties-workspaces-workspace-bundleid.md.properties.json

for resource, resource_data in cfn['ResourceTypes'].items():
    print(resource) 
    if "Documentation" in resource_data:
        filename = resource_data['Documentation'].split('.html')[0].split('/')[-1]
        filepath = "./doc_source/%s.md.properties.json" % (filename)
        resource_docs_data = json.load(open(filepath))
        # filefound =  os.path.isfile(filepath)
        # print(filepath)
        # if filefound:
        #    print('\t\t[%s] %s' % (filefound, filepath) )

   
    print("CFN Specication data")
    print(json.dumps(cfn['ResourceTypes'][resource]["Properties"],indent=4))

    for property_name, property_data in cfn['ResourceTypes'][resource]["Properties"].items():
        print('\t%s.%s' % (resource, property_name) )
        # print(json.dumps(property_data, indent=4))
        if "Documentation" in property_data:

            filename = property_data["Documentation"].split('.html')[0].split('/')[-1]
            filepath = "./doc_source/%s.md.properties.json" % (filename)
            print(filepath)
            property_docs_data = json.load(open(filepath))[property_name]
            # filefound =  os.path.isfile(filepath)
            # if filefound:
            #    print('\t\t[%s] %s' % (filefound, filepath) )
            keys = list(property_docs_data.keys())
            for k  in keys:
                v = property_docs_data[k]
                k2 = k.split('.')[-1]
                property_docs_data[k2] = v
                del property_docs_data[k]


            
            
            print("DOCs Spec")
            print(json.dumps(property_docs_data, indent=4))
            sys.exit()

#print(json.dumps(list(allowed_values),indent=4))




