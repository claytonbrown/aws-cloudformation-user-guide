import sys
import json


output = {}
properties = {}
pipe = sys.stdin.read()
pipe = pipe.split("# ")
for data in pipe:
    # print(data)
    if "Properties<a" in data:
        property_type = data.split("Properties<a name=\"")[1].split('\"')[0]
        property_type = property_type.replace("aws-resource-","")  # .replace("-properties","")
        for property in data.split("\n`"):
            if "Properties<a " not in property:
                property_name = property.split("`")[0]
                property_bag = property.split("\n*")
                # pprint.pprint(property_bag)
                # property_name = property_type.rstrip("properties") + property_name.lower()
                properties[property_name] = {}
                ok = True
                for prop in property_bag:
                    if "*" in prop:
                        # print(prop)
                        try:
                            items = prop.split("*: ")

                            # print(items)
                            property_key = items[0].strip()

                            property_data = items[1].strip().strip('`')

                            if property_key == "Type":
                                # "Type": "[TaskInvocationParameters](aws-properties-ssm-maintenancewindowtask-taskinvocationparameters.md)"
                                property_data = property_data.split(']')[0].strip('[')

                                if property_data == "Boolean":
                                    properties[property_name]["AllowedValues"] = ["True", "False"]


                            if property_key == "Update requires":
                                property_key = "UpdateRequires"
                                # "Update requires": "[Replacement](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-replacement)\n\n#"
                                property_data = property_data.split(']')[0].strip('[')

                            if property_key == "Allowed Values":
                                property_key = "AllowedValues"
                                # "Update requires": "[Replacement](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-replacement)\n\n#"
                                property_data = property_data.split(' | ')
                        except:
                            ok = False
                            pass
                            # print("im here")
                            # print(prop)



                        if ok:
                            properties[property_name][property_key] = property_data

        output[property_type] = properties
print(
    json.dumps(output, indent=4)
)
