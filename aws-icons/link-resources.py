import glob
import json

def link_icons(schema_file = "../CloudFormationResourceSpecification.json", files_glob = 'latest/*/*/**/*.png'):
    service_icons = {}
    cfn_schema = None
    matched = 0
    unmatched = 0

    with open(schema_file, 'r') as f:
        cfn_schema = json.loads(f.read())
        f.close()
    
    for file in sorted(glob.glob(files_glob)):
        file_key = file.split('/')[-1].split("_")[1].split(".png")[0].lower().replace("amazon-","").replace("aws-","").strip()
        split_filename = file_key.split('_')
        service_name, shade, size = None, 'unknown', None 

        if len(split_filename) == 1:
            service_name = split_filename[0]
            
        if len(split_filename) == 2:
            service_name, size = split_filename

        elif len(split_filename) == 3:
            service_name, shade, size = split_filename
        else:
            print(split_filename)

        if service_name not in service_icons:
            service_icons[service_name] = {}

        if size not in service_icons[service_name]:
            service_icons[service_name][size] = file
        


    # print(json.dumps(service_icons, indent=4))
    
    for resource_type in cfn_schema["ResourceTypes"]:
        service_name = resource_type.replace("::","-").lower().replace("amazon-","").replace("aws-","").strip()

        if service_name in service_icons:
            cfn_schema["ResourceTypes"][resource_type]["Icons"] = service_icons[service_name]
            print("Matched: %s" % (service_name))
            matched += 1
        elif service_name.split('-')[0] in service_icons:
            cfn_schema["ResourceTypes"][resource_type]["Icons"] = service_icons[service_name.split('-')[0]]
            print("Matched: %s" % (service_name.split('-')[0]))
            matched += 1
        
        else:
            print("Unmatched: %s" % (service_name))
            unmatched += 1

    # print(json.dumps(cfn_schema["ResourceTypes"], indent=4))
    # print(json.dumps(list(service_icons.keys()), indent=4))
    print("Matched: %s" % (matched))
    print("Unmatched: %s" % (unmatched))

    with open("../CLoudFormationResourceSpecificationWithIcons.json", 'w') as f:
        f.write(json.dumps(cfn_schema, indent=4))
        f.close()
        print("Written: ../CLoudFormationResourceSpecificationWithIcons.json")

if __name__ == '__main__':
    link_icons()