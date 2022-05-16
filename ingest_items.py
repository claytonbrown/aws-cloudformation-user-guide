import json
import glob
import boto3

def collate_properties(path='./doc_source/aws-resources-*.json'):
    response = {}
    for file in glob.glob(path):

        print(file)
        with open(file, 'r') as f:
            data = json.loads(f.read())
            f.close()
        # print(json.dumps(data, indent=4))
    return response

def collate(type):
    response = {}

    for file in glob.glob('./doc_source/aws-%s-*.json' % (type)):
        key = file.split(type)[1].split('.')[0][1:]
        try:
            with open(file, 'r') as f:
                data = json.loads(f.read())
                f.close()
                # print(json.dumps(data, indent=4))
                """
                {
                    "wafv2.webacl.managedrulegroupconfig.LoginPath": {
                        "Required": "No",
                        "Type": "String",
                        "Minimum": "1",
                        "Maximum": "256",
                        "Pattern": ".*\\S.*",
                        "UpdateRequires": "[No interruption](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-no-interrupt)"
                    },
                    "wafv2.webacl.managedrulegroupconfig.PasswordField": {
                        "Required": "No",
                        "Type": "FieldIdentifier",
                        "UpdateRequires": "[No interruption](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-no-interrupt)"
                    },
                    "wafv2.webacl.managedrulegroupconfig.PayloadType": {
                        "Required": "No",
                        "Type": "String",
                        "Allowed values": "FORM_ENCODED | JSON",
                        "UpdateRequires": "[No interruption](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-no-interrupt)"
                    },
                    "wafv2.webacl.managedrulegroupconfig.UsernameField": {
                        "Required": "No",
                        "Type": "FieldIdentifier",
                        "UpdateRequires": "[No interruption](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-no-interrupt)"
                    }
                }
                """
                for k in data.keys():
                    response[k.lower().strip()] = data[k]

            print("Ok: [%s] %s" % (key, file))
        except:
            print("Error: %s" % file)
        # print(json.dumps(data, indent=4))
    return response

if __name__ == "__main__":
    result = {
        "resources":  collate(type='resource'),
        "properties":  collate(type='properties')
    }
    outfile = './data/cfn-properties.json'
    with open(outfile,'w') as f:
        f.write(json.dumps(result, indent=4))
        f.close()
        print("Written: %s" % (outfile))
