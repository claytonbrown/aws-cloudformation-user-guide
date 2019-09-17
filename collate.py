import glob
import json
import csv
import os

f = csv.writer(open("test.csv", "w", newline=''))
f.writerow(["resource", "model", "codename", "name", "content_type"])

spec = {
    "ResourceTypes": {},
    "PropertyTypes": {},
    "Docs2Resource": {}
}

spec["PropertyTypes"]["String"] = "example-string"
spec["PropertyTypes"]["Boolean"] = "True"
spec["PropertyTypes"]["Integer"] = 1
spec["PropertyTypes"]["Long"] = 123.4
spec["PropertyTypes"]["Double"] = 123.45
spec["PropertyTypes"]["Float"] = 1.23456789
spec["PropertyTypes"]["Json"] = {"todo": "json"}
spec["PropertyTypes"]["Timestamp"] = "1970-01-01T01:02:30.070Z"

all_keys = set()


def expand_property(cfn_ref, property_name, data):
    cfn_ref = ""
    return


# Enumerate all Resources
for file in glob.glob("doc_source/AWS_*"):
    with open(file, 'r') as f:
        for line in f.readlines():
            if "+" in line:
                resource = line.split("]")[0].split('[')[1]
                key = resource.lower().replace('::', '-')
                # print((resource, key))
                spec["Docs2Resource"][key] = resource


# Enumerate all resource Properties
for file in glob.glob('doc_source/aws-properties-*.json'):
    # print(file)
    # e.g. aws-properties-amplify-branch-environmentvariable.md.properties.json
    with open(file, 'r') as f:
        try:
            data = json.loads(f.read())
            for key in data.keys():
                docs_key = key.replace("aws-properties-", "")
                spec["PropertyTypes"][docs_key] = data[key]
        except Exception as e:
            print(e)
            pass

types = {}
# Enumerate all resource Types
for file in sorted(glob.glob('doc_source/aws-resource-*.json')):
    # print(file)
    with open(file, 'r') as f:

        data = json.loads(f.read())

        # extract single key for resource definition and value
        for key in data.keys():
            try:
                docs_key = 'aws-%s' % (key.replace("-properties", ""))
                if docs_key not in spec["Docs2Resource"]:
                    docs_key = 'aws-resource-%s' % (key.replace("-properties", ""))

                resource = spec["Docs2Resource"][docs_key]

                spec["ResourceTypes"][resource] = data[key]

                for k, v in data[key].items():
                    # "amazonmq-broker-configurationid-properties"
                    # print(k)

                    docs_property_key = "%s-%s-properties" % (resource.lower().replace("::", "-"), k.lower())
                    field_ref = resource + '.' + k

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

                        for property_name in data[key][k].keys():
                            property_name = property_name.split('`')[0]
                            if property_name not in all_keys:
                                all_keys.add(property_name)

                        property_key = "%s-%s-%s" % (resource, key, field_type.lower())
                        if len(field_type) > 0:
                            if field_type not in types:
                                types[field_type] = []
                            propKey = key.replace("-properties", "-%s-properties" % (field_type.lower()))
                            sample = ''
                            if propKey in spec["PropertyTypes"]:
                                sample = spec["PropertyTypes"][propKey]
                                spec["ResourceTypes"][field_ref]["CloudPropertySample"] = sample

                            types[field_type].append([propKey, sample])
                        # print(json.dumps(v, indent=4))

            except Exception as e:
                print("Exception")
                print((file, key))
                print(e)

print(json.dumps(types, indent=4))
print(json.dumps(sorted(list(all_keys)), indent=4))

with open("spec.json", 'w') as f:
    f.write(json.dumps(spec, indent=4))
    print("written json")
