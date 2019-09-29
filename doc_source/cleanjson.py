import sys
import json
# import yaml


def clean_json(d):
    new = {}
    for k, v in d.items():
        if isinstance(v, dict):
            v = clean_json(v)
        new_k = k.split('<')[0].strip()

        if new_k == 'JSON':
            v = "[%s]" % (
                v.replace('\n', '').replace("```", "").replace('\\', '')
            )
            # print(v)
            # v = json.loads(v)  #
        # if new_k == 'YAML':
        #    v = yaml.load(v)

        new[new_k] = v
    return new


print(
    json.dumps(
        clean_json(
            json.load(sys.stdin)
        ),
        indent=4
    )
)
