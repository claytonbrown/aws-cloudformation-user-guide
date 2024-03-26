git submodule update --init
git pull upstream main
cd aws-cfn-resource-specs
git pull 
cd ..
cp cp aws-cfn-resource-specs/specs/us-east-1/CloudFormationResourceSpecification.json ./CloudFormationResourceSpecification.json
curl https://awspolicygen.s3.amazonaws.com/js/policies.js | sed '1s/[^=]*=//' | jq '[.serviceMap[]]' | jq 'map( { (.StringPrefix|tostring): . } ) | add' > ./aws_service_info/aws_organizations_support.json

# Update IAM reference
curl https://raw.githubusercontent.com/witoff/aws-iam-reference/master/reference.json | jq . > ./aws_service_info/iam_reference.json

# Update Endpoints
curl https://raw.githubusercontent.com/boto/botocore/develop/botocore/data/endpoints.json | jq . > ./aws_service_info/api_endpoints.json

# Update EC2 Types
python3 vantage_scrape.py| jq . > ./aws_service_info/ec2_instances.json

# Process Resources
OVERWRITE=False

for document in `ls doc_source/aws-resource*.md`; do
	# echo $document;
	FILE="$document.properties.json"
	if [ ! -f $FILE ]; then
		cat $document | python3 cfn_properties_json.py | jq . > $FILE
		echo "Generated $document.properties.json"
	else
		echo "File $FILE exists."
	fi
done;

# Process Resource Properties
for document in `ls doc_source/aws-properties-*.md`; do
	# echo $document;
	FILE="$document.properties.json"
	if [ ! -f $FILE ]; then
		cat $document | python3 cfn_properties_json.py | jq . > $FILE
		echo "Generated $document.properties.json"
	else
		echo "File $FILE exists."
	fi
done;

# Collate
python3 collate.py
python3 summarize.py

# Publish new cloudformation guard generated ruleset
cp -R rulesets/* cloudformation-guard/Examples/

 