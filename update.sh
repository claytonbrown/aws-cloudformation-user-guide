# Update to latest CFN spec 
git pull upstream main
cp ../cfn_resource_specs/CloudFormationResourceSpecification-us-east-1.json ./CloudFormationResourceSpecification.json
curl https://awspolicygen.s3.amazonaws.com/js/policies.js | sed '1s/[^=]*=//' | jq '[.serviceMap[]]' | jq 'map( { (.StringPrefix|tostring): . } ) | add' > ./aws_service_info/aws_organizations_support.json
# Process Resources
for document in `ls doc_source/aws-resource*.md`; do
	# echo $document;
	cat $document | python cfn_properties_json.py | jq . > "$document.properties.json"
	echo "Generated $document.properties.json"
done;

# Process Resource Properties
for document in `ls doc_source/aws-properties-*.md`; do
	# echo $document;
	cat $document | python cfn_properties_json.py | jq . > "$document.properties.json"
	echo "Generated $document.properties.json"
done;

# Collate
python3 collate.py
python3 summarize.py

# Publish new cloudformation guard generated ruleset
cp cfndecorator.ruleset ../../utils/cloudformation-guard/Examples/
