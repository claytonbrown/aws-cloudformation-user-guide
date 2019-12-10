import json
import logging

# aws-properties-autoscalingplans-scalingplan-scalinginstruction.md:*Allowed Values*: `KeepExternalPolicies | ReplaceExternalPolicies`
properties = {}

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
            # print(line)
            # print(e)
            logging.debug(e)
            pass

    # work with exceptions
    properties["glue.job.jobcommand.pythonversion"] = ["2", "3"]
    properties["appsync.graphqlapi.authenticationtype"] = ["API_KEY", "AWS_IAM", "AMAZON_COGNITO_USER_POOLS", "OPENID_CONNECT"]

print(json.dumps(properties, indent=4))
output_file = input_file.replace(".txt", ".json")
with open(output_file, 'w') as file:
    file.write(json.dumps(properties, indent=4))
    file.close()
    print("Written: %s" % (output_file))
