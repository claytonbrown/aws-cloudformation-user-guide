cp ../cfn_resource_specs/CloudFormationResourceSpecification-us-east-1.json ./CloudFormationResourceSpecification.json

for document in `ls doc_source/aws-properties-*.md`; do
	echo $document;
	cat $document | python cfn_properties_json.py | jq .
done;
