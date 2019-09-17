for document in `ls doc_source/aws-resource*.md`; do
	# echo $document;
	cat $document | python cfn_properties_json.py | jq . > "$document.properties.json"
	echo "Generated $document.properties.json"
done;

for document in `ls doc_source/aws-properties-*.md`; do
	# echo $document;
	cat $document | python cfn_properties_json.py | jq . > "$document.properties.json"
	echo "Generated $document.properties.json"
done;

python3 collate.py
python3 summarize.py

