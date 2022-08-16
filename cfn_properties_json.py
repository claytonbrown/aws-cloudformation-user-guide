import sys
import json
import pprint
import re
import inflection

CLEANR = re.compile('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});')

def cleanhtml(raw_html):
  cleantext = re.sub(CLEANR, '', raw_html).replace("\n","").replace("\\","").strip()
  return cleantext


debug = False
output = {}
properties = {}
result = {}
pipe = sys.stdin.read()
pipe = pipe.split("# ")


for data in pipe:
    firstline = data.split("\n")[0]

    if 'AWS::' in firstline and "aws-resource-" in firstline: 
        # AWS::RDS::DBCluster<a name="aws-resource-rds-dbcluster"></a>
        
        properties["CfnAbout"] = data.split("</a>")[1].split('#')[0].strip().replace("\\","")
        properties['CfnType'] = firstline.split('<a')[0].replace('# ','').strip().replace(' ','.')
        properties['CfnDocsKey'] = firstline.split('"')[1].split('"')[0].replace('#','').strip().split('.')[0]

    if 'AWS::' in firstline and "aws-properties-" in firstline: 
        # AWS::Redshift::Cluster Endpoint<a name="aws-properties-redshift-cluster-endpoint"></a>
        firstline = data.split("##")[0].split('*')[0]
        properties["CfnAbout"] = data.split("</a>")[1].split('#')[0].strip().replace("\\","")
        properties['CfnType'] = firstline.split('<a')[0].replace('# ','').strip().replace(' ','.')
        properties['CfnDocsKey'] = firstline.split('"')[1].split('"')[0].replace('#','').strip().split('.')[0]

    # print(data)
    if "Properties<a" in data:
        property_type = data.split("Properties<a name=\"")[1].split('\"')[0]
        property_type = property_type.replace("aws-resource-", "")  # .replace("-properties","")
        split_data = data.split("\n`")
        if debug:
            pprint.pprint(split_data)
            # sys.exit(1)
        for property in split_data:

            try:
                doc_text = cleanhtml("".join(property).split("\n*")[0].split("</a>\n")[1])
            except:
                doc_text = ""

            if "Properties<a " not in property:
                property_name = property.split("`")[0]
                property_bag = property.split("\n*")
                if debug:
                    pprint.pprint(property_bag)
                # property_name = property_type.rstrip("properties") + property_name
                properties[property_name] = {}
                ok = True
                for prop in property_bag:

                    if "*" in prop:
                        # print(prop)
                        try:
                            properties[property_name]["Description"] = doc_text
                            items = prop.split("*: ")

                            # print(items)
                            property_key = items[0].strip()

                            property_data = items[1].strip().strip('`')

                            if property_key == "Type":
                                # "Type": "[TaskInvocationParameters](aws-properties-ssm-maintenancewindowtask-taskinvocationparameters.md)"
                                property_data = property_data.split(']')[0].strip('[')

                                if property_data == "Boolean":
                                    properties[property_name]["AllowedValues"] = ["True", "False"]


                            if "Type" in property_key:
                                properties[property_name]["Type"] = property_data.strip('')

                            if "Pattern" in property_key:
                                properties[property_name]["Pattern"] = property_data.strip('')

                            if "Maximum" in property_key:
                                properties[property_name]["Maximum"] = property_data.strip('')

                            if "Minimum" in property_key:
                                properties[property_name]["Minimum"] = property_data.strip('')

                            if "Required" in property_key:
                                property_key = "Required"
                                # "Update requires": "[Replacement](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-replacement)\n\n#"
                                properties[property_name]["Required"] = property_data.strip('')

                            if "Update requires" in property_key:
                                property_key = "UpdateRequires"
                                # "Update requires": "[Replacement](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-replacement)\n\n#"
                                properties[property_name]["UpdateRequires"] = property_data.split(']')[0].strip('[')

                            if "Allowed Values" in property_key:
                                # "Update requires": "[Replacement](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-replacement)\n\n#"
                                properties[property_name]["AllowedValues"] = property_data.split(' | ')
                        except:
                            ok = False
                            pass
                            # print("im here")
                            # print(prop)

                        if ok:
                            properties[property_name][property_key] = property_data

        output[property_type.lower()] = properties

        # flatten properties into their own keys

        for k1, v1 in output.items():
            if isinstance(v1, dict):
                for k2, v2 in v1.items():
                    norm_key = k1.replace("aws-properties-", "").replace("-properties", "").replace('-', '.') + '.' + k2
                    property_key = norm_key
                    result[property_key] = v2

        # for k1, v1 in output.items():
        #   if '-properties' in k1:
        #       del output[k1]


print(
    json.dumps(result, indent=4)
)
